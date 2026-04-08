"""Shared test fixtures for django-rspack tests."""

from __future__ import annotations

import json

import pytest

from django_rspack.conf import RspackConfiguration, reset_config
from django_rspack.manifest import Manifest, reset_manifest


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset cached singletons between tests."""
    reset_config()
    reset_manifest()
    yield
    reset_config()
    reset_manifest()


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project directory structure."""
    (tmp_path / "app" / "javascript" / "packs").mkdir(parents=True)
    (tmp_path / "public" / "packs").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "tmp" / "rspack").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_manifest_data():
    """Return a sample manifest.json structure."""
    return {
        "application.js": "/packs/application-abc123.js",
        "application.css": "/packs/application-def456.css",
        "vendor.js": "/packs/vendor-789xyz.js",
        "entrypoints": {
            "application": {
                "assets": {
                    "js": [
                        "/packs/runtime-abc123.js",
                        "/packs/vendor-789xyz.js",
                        "/packs/application-abc123.js",
                    ],
                    "css": [
                        "/packs/application-def456.css",
                    ],
                }
            }
        },
        "images/logo.png": "/packs/images/logo-aaa111.png",
    }


@pytest.fixture
def manifest_file(tmp_project, sample_manifest_data):
    """Write sample manifest.json to the tmp project."""
    manifest_path = tmp_project / "public" / "packs" / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest_data))
    return manifest_path


@pytest.fixture
def config_with_manifest(tmp_project, manifest_file, settings):
    """Create a config that points to the tmp project with a manifest."""
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {
        "source_path": "app/javascript",
        "source_entry_path": "packs",
        "public_root_path": "public",
        "public_output_path": "packs",
    }
    return RspackConfiguration()


@pytest.fixture
def manifest_with_data(config_with_manifest):
    """Create a Manifest instance backed by sample data."""
    return Manifest(config=config_with_manifest)
