"""Tests for django_rspack.compiler."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from django_rspack.compiler import compile_assets, is_stale
from django_rspack.conf import RspackConfiguration


class TestCompiler:
    @pytest.fixture
    def config(self, tmp_project, settings):
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        return RspackConfiguration()

    def test_is_stale_when_no_manifest(self, config):
        """Should be stale when manifest doesn't exist."""
        assert is_stale(config) is True

    def test_is_stale_with_fresh_manifest(self, config, tmp_project, sample_manifest_data):
        """Should not be stale when manifest is newer than sources."""
        # Create manifest
        manifest_path = tmp_project / "public" / "packs" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest_data))
        # No source files => not stale
        assert is_stale(config) is False

    def test_is_stale_mtime_with_newer_source(self, config, tmp_project, sample_manifest_data):
        """Should be stale when source is newer than manifest (mtime strategy)."""
        import time

        # Create manifest first
        manifest_path = tmp_project / "public" / "packs" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest_data))

        # Wait briefly then create a source file
        time.sleep(0.05)
        source_file = tmp_project / "app" / "javascript" / "packs" / "application.js"
        source_file.write_text("console.log('hello');")

        assert is_stale(config) is True

    @patch("django_rspack.compiler.subprocess.run")
    def test_compile_success(self, mock_run, config, tmp_project):
        """Should return True on successful compilation."""
        mock_run.return_value.returncode = 0

        # Create a fake rspack binary
        bin_dir = tmp_project / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        rspack_bin = bin_dir / "rspack"
        rspack_bin.write_text("#!/bin/sh\nexit 0")
        rspack_bin.chmod(0o755)

        result = compile_assets(config)
        assert result is True
        mock_run.assert_called_once()

    @patch("django_rspack.compiler.subprocess.run")
    def test_compile_failure(self, mock_run, config, tmp_project):
        """Should return False on failed compilation."""
        mock_run.return_value.returncode = 1

        bin_dir = tmp_project / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        rspack_bin = bin_dir / "rspack"
        rspack_bin.write_text("#!/bin/sh\nexit 1")
        rspack_bin.chmod(0o755)

        result = compile_assets(config)
        assert result is False

    @patch("django_rspack.compiler.subprocess.run")
    def test_compile_with_config_file(self, mock_run, config, tmp_project):
        """Should pass --config when a config file exists."""
        mock_run.return_value.returncode = 0

        bin_dir = tmp_project / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "rspack").write_text("#!/bin/sh")
        (bin_dir / "rspack").chmod(0o755)

        # Create config file
        (tmp_project / "rspack.config.js").write_text("module.exports = {};")

        compile_assets(config)
        call_args = mock_run.call_args[0][0]
        assert "--config" in call_args

    @patch("django_rspack.compiler.subprocess.run", side_effect=FileNotFoundError)
    def test_compile_binary_not_found(self, mock_run, config):
        """Should return False and print error when rspack binary not found."""
        result = compile_assets(config)
        assert result is False
