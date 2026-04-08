"""Tests for django_rspack.manifest."""

from __future__ import annotations

import json

import pytest

from django_rspack.manifest import Manifest, MissingEntryError, get_manifest, reset_manifest


class TestManifest:
    def test_lookup_existing_asset(self, manifest_with_data):
        """Should return the fingerprinted path for a known asset."""
        result = manifest_with_data.lookup("application.js")
        assert result == "/packs/application-abc123.js"

    def test_lookup_by_name_and_type(self, manifest_with_data):
        """Should resolve name + type to the correct path."""
        result = manifest_with_data.lookup("application", pack_type="js")
        assert result == "/packs/application-abc123.js"

    def test_lookup_css(self, manifest_with_data):
        """Should find CSS assets."""
        result = manifest_with_data.lookup("application.css")
        assert result == "/packs/application-def456.css"

    def test_lookup_missing_returns_none(self, manifest_with_data):
        """Should return None for missing assets."""
        result = manifest_with_data.lookup("nonexistent.js")
        assert result is None

    def test_lookup_strict_raises_on_missing(self, manifest_with_data):
        """lookup_strict should raise MissingEntryError for missing assets."""
        with pytest.raises(MissingEntryError, match="Can't find nonexistent.js"):
            manifest_with_data.lookup_strict("nonexistent.js")

    def test_lookup_strict_returns_path(self, manifest_with_data):
        """lookup_strict should return the path for existing assets."""
        result = manifest_with_data.lookup_strict("application.js")
        assert result == "/packs/application-abc123.js"

    def test_lookup_pack_with_chunks(self, manifest_with_data):
        """Should return all JS chunks for an entry point."""
        chunks = manifest_with_data.lookup_pack_with_chunks("application", pack_type="js")
        assert chunks == [
            "/packs/runtime-abc123.js",
            "/packs/vendor-789xyz.js",
            "/packs/application-abc123.js",
        ]

    def test_lookup_pack_with_chunks_css(self, manifest_with_data):
        """Should return CSS chunks for an entry point."""
        chunks = manifest_with_data.lookup_pack_with_chunks("application", pack_type="css")
        assert chunks == ["/packs/application-def456.css"]

    def test_lookup_pack_with_chunks_missing(self, manifest_with_data):
        """Should return None for missing entry points."""
        chunks = manifest_with_data.lookup_pack_with_chunks("nonexistent", pack_type="js")
        assert chunks is None

    def test_lookup_pack_with_chunks_strict(self, manifest_with_data):
        """Strict chunk lookup should raise on missing entry."""
        with pytest.raises(MissingEntryError):
            manifest_with_data.lookup_pack_with_chunks_strict("nonexistent", pack_type="js")

    def test_missing_manifest_file(self, tmp_project, settings):
        """Should handle missing manifest gracefully."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        assert manifest.lookup("application.js") is None

    def test_missing_manifest_strict_error_message(self, tmp_project, settings):
        """Should provide helpful error when manifest doesn't exist."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        with pytest.raises(MissingEntryError, match="manifest file not found"):
            manifest.lookup_strict("application.js")

    def test_empty_manifest_file(self, tmp_project, settings):
        """Should handle an empty manifest file."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        (tmp_project / "public" / "packs" / "manifest.json").write_text("")
        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        assert manifest.lookup("application.js") is None

    def test_empty_manifest_strict_error(self, tmp_project, settings):
        """Should report empty manifest as still-compiling."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        (tmp_project / "public" / "packs" / "manifest.json").write_text("")
        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        with pytest.raises(MissingEntryError, match="manifest is empty"):
            manifest.lookup_strict("application.js")

    def test_manifest_caching_in_production(self, tmp_project, settings, sample_manifest_data):
        """Manifest should be cached when cache_manifest is True."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = False
        settings.RSPACK = {"cache_manifest": True}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        manifest_path = tmp_project / "public" / "packs" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest_data))

        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        # First lookup loads the manifest
        assert manifest.lookup("application.js") == "/packs/application-abc123.js"

        # Modify the file on disk
        new_data = {"application.js": "/packs/application-NEW.js"}
        manifest_path.write_text(json.dumps(new_data))

        # Should still return cached value
        assert manifest.lookup("application.js") == "/packs/application-abc123.js"

    def test_manifest_reload_in_development(self, tmp_project, settings, sample_manifest_data):
        """Manifest should reload on every request in development."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {"cache_manifest": False}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        manifest_path = tmp_project / "public" / "packs" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest_data))

        from django_rspack.conf import RspackConfiguration

        config = RspackConfiguration()
        manifest = Manifest(config=config)

        assert manifest.lookup("application.js") == "/packs/application-abc123.js"

        # Modify the file on disk
        new_data = {"application.js": "/packs/application-NEW.js"}
        manifest_path.write_text(json.dumps(new_data))

        # Should return new value
        assert manifest.lookup("application.js") == "/packs/application-NEW.js"

    def test_refresh(self, manifest_with_data, manifest_file, sample_manifest_data):
        """refresh() should force reload from disk."""
        # Initial load
        assert manifest_with_data.lookup("application.js") == "/packs/application-abc123.js"

        # Modify manifest
        new_data = {**sample_manifest_data, "application.js": "/packs/application-REFRESHED.js"}
        manifest_file.write_text(json.dumps(new_data))

        manifest_with_data.refresh()
        assert manifest_with_data.lookup("application.js") == "/packs/application-REFRESHED.js"

    def test_image_asset_lookup(self, manifest_with_data):
        """Should look up image assets from the manifest."""
        result = manifest_with_data.lookup("images/logo.png")
        assert result == "/packs/images/logo-aaa111.png"

    def test_get_manifest_caches(self, config_with_manifest, settings):
        """get_manifest() should return the same instance."""
        reset_manifest()
        m1 = get_manifest()
        m2 = get_manifest()
        assert m1 is m2
