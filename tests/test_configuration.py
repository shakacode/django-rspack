"""Tests for django_rspack.conf."""

from __future__ import annotations

import pytest

from django_rspack.conf import RspackConfiguration, get_config, reset_config


@pytest.mark.django_db
class TestConfiguration:
    def test_defaults_in_development(self, tmp_project, settings):
        """Development mode should have compile=True and no manifest caching."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        config = RspackConfiguration()

        assert config.env == "development"
        assert config.compile is True
        assert config.cache_manifest is False

    def test_defaults_in_production(self, tmp_project, settings):
        """Production mode should have compile=False and manifest caching."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = False
        settings.RSPACK = {}
        config = RspackConfiguration()

        assert config.env == "production"
        assert config.compile is False
        assert config.cache_manifest is True

    def test_django_settings_override(self, tmp_project, settings):
        """Django settings should override YAML and defaults."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {
            "source_path": "frontend/src",
            "public_output_path": "assets",
            "compile": False,
        }
        config = RspackConfiguration()

        assert config.source_path == tmp_project / "frontend" / "src"
        assert config.public_output_path == tmp_project / "public" / "assets"
        assert config.compile is False

    def test_yaml_config_loading(self, tmp_project, settings):
        """Config should load from shakapacker.yml."""
        yaml_content = """\
development:
  source_path: custom/js
  public_output_path: custom-packs
  compile: true
"""
        (tmp_project / "config").mkdir(parents=True, exist_ok=True)
        (tmp_project / "config" / "shakapacker.yml").write_text(yaml_content)

        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        config = RspackConfiguration()

        assert config.source_path == tmp_project / "custom" / "js"
        assert config.public_output_path == tmp_project / "public" / "custom-packs"

    def test_manifest_path_default(self, tmp_project, settings):
        """Default manifest path should be public_output_path/manifest.json."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        config = RspackConfiguration()

        assert config.manifest_path == tmp_project / "public" / "packs" / "manifest.json"

    def test_manifest_path_custom(self, tmp_project, settings):
        """Custom manifest_path should override the default."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {"manifest_path": "build/manifest.json"}
        config = RspackConfiguration()

        assert config.manifest_path == tmp_project / "build" / "manifest.json"

    def test_dev_server_config(self, tmp_project, settings):
        """Dev server config should be accessible."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {
            "dev_server": {
                "host": "0.0.0.0",
                "port": 8080,
                "server": "https",
            }
        }
        config = RspackConfiguration()

        assert config.dev_server_host == "0.0.0.0"
        assert config.dev_server_port == 8080
        assert config.dev_server_protocol == "https"
        assert config.dev_server_url == "https://0.0.0.0:8080"

    def test_dev_server_env_override(self, tmp_project, settings, monkeypatch):
        """Environment variables should override dev server config."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        monkeypatch.setenv("RSPACK_DEV_SERVER_HOST", "my-host")
        monkeypatch.setenv("RSPACK_DEV_SERVER_PORT", "9999")
        config = RspackConfiguration()

        assert config.dev_server_host == "my-host"
        assert config.dev_server_port == 9999

    def test_asset_host(self, tmp_project, settings):
        """Asset host should be configurable."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = False
        settings.RSPACK = {"asset_host": "https://cdn.example.com"}
        config = RspackConfiguration()

        assert config.asset_host == "https://cdn.example.com"

    def test_asset_host_env_override(self, tmp_project, settings, monkeypatch):
        """RSPACK_ASSET_HOST env var should override config."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = False
        settings.RSPACK = {"asset_host": "https://cdn.example.com"}
        monkeypatch.setenv("RSPACK_ASSET_HOST", "https://other-cdn.example.com")
        config = RspackConfiguration()

        assert config.asset_host == "https://other-cdn.example.com"

    def test_env_override(self, tmp_project, settings, monkeypatch):
        """RSPACK_ENV should override the auto-detected environment."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        monkeypatch.setenv("RSPACK_ENV", "production")
        config = RspackConfiguration()

        assert config.env == "production"

    def test_get_config_caches(self, tmp_project, settings):
        """get_config() should return the same instance."""
        settings.BASE_DIR = str(tmp_project)
        settings.RSPACK = {}
        reset_config()

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config(self, tmp_project, settings):
        """reset_config() should clear the cached instance."""
        settings.BASE_DIR = str(tmp_project)
        settings.RSPACK = {}
        reset_config()

        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2

    def test_integrity_config(self, tmp_project, settings):
        """Integrity configuration should be accessible."""
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = False
        settings.RSPACK = {
            "integrity": {
                "enabled": True,
                "hash_functions": ["sha256", "sha384"],
                "cross_origin": "use-credentials",
            }
        }
        config = RspackConfiguration()

        assert config.integrity_enabled is True
        assert config.integrity_hash_functions == ["sha256", "sha384"]
        assert config.integrity_cross_origin == "use-credentials"

    def test_invalid_yaml_raises(self, tmp_project, settings):
        """Invalid YAML should raise a clear error."""
        (tmp_project / "config").mkdir(parents=True, exist_ok=True)
        (tmp_project / "config" / "shakapacker.yml").write_text(
            "development:\n  source_path: [\n  invalid yaml"
        )
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}

        with pytest.raises(ValueError, match="YAML syntax error"):
            RspackConfiguration()
