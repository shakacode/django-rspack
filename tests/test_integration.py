"""
Integration / regression tests for django-rspack.

These tests boot a real Django project (tests/testapp_settings.py) and exercise
the full request cycle: URL routing → view → template tag → manifest lookup →
HTML response. They catch wiring issues that isolated unit tests miss:

- AppConfig.ready() fires and conf module loads
- Template tag library is discoverable via {% load rspack %}
- Middleware hooks into the request/response cycle
- Management commands are discoverable
- manifest.json is read through the config → manifest → template tag chain
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command, get_commands
from django.test import Client, override_settings

# Import the settings dict so every test in this module uses the integration project
from tests.testapp_settings import MANIFEST_DATA, TESTAPP_SETTINGS

# Apply the full settings to every test in this module
pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _apply_settings():
    """Return an override_settings context with the integration project."""
    return override_settings(**TESTAPP_SETTINGS)


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
class TestAppWiring:
    """Verify the Django app loads and all extension points register."""

    def test_app_is_installed(self):
        """django_rspack should be in INSTALLED_APPS and loadable."""
        from django.apps import apps

        assert apps.is_installed("django_rspack")

    def test_app_config_ready_runs(self):
        """AppConfig.ready() should import conf without error."""
        from django.apps import apps

        config = apps.get_app_config("django_rspack")
        assert config.verbose_name == "Django Rspack"

    def test_templatetag_library_registered(self):
        """The 'rspack' template library should be loadable."""
        from django.template import engines

        engine = engines["django"]
        # This will raise if the library isn't registered
        engine.from_string("{% load rspack %}")


# ---------------------------------------------------------------------------
# Management commands
# ---------------------------------------------------------------------------
class TestManagementCommands:
    """Verify management commands are discoverable and callable."""

    def test_commands_registered(self):
        """All three management commands should be discoverable."""
        commands = get_commands()
        assert "rspack_install" in commands
        assert "rspack_dev_server" in commands
        assert "rspack_compile" in commands

    def test_rspack_compile_command_runs(self):
        """rspack_compile should be callable (will fail due to no rspack binary, but should not crash on import)."""
        with _apply_settings():
            out = StringIO()
            # It will fail because there's no rspack binary, but it should
            # get past argument parsing and into the handler
            with pytest.raises(SystemExit):
                call_command("rspack_compile", stdout=out, stderr=StringIO())

    def test_rspack_install_command_runs(self):
        """rspack_install should run and create files."""
        with _apply_settings():
            out = StringIO()
            call_command("rspack_install", stdout=out)
            output = out.getvalue()
            assert "django-rspack installed successfully" in output


# ---------------------------------------------------------------------------
# Full request cycle: URL → View → Template tag → Manifest → HTML
# ---------------------------------------------------------------------------
class TestFullRequestCycle:
    """End-to-end tests through Django's request handling."""

    def test_index_page_renders_js_and_css(self):
        """GET / should render a page with <script> and <link> tags from manifest."""
        with _apply_settings():
            from django_rspack.conf import reset_config
            from django_rspack.manifest import reset_manifest

            reset_config()
            reset_manifest()

            client = Client()
            response = client.get("/")

        assert response.status_code == 200
        html = response.content.decode()

        # CSS should be in <head>
        assert '<link rel="stylesheet" href="/packs/application-4d5e6f.css"' in html

        # JS should include all chunks from entrypoints (runtime, vendors, application)
        assert "/packs/runtime-aaa111.js" in html
        assert "/packs/vendors-bbb222.js" in html
        assert "/packs/application-1a2b3c.js" in html

        # Scripts should have defer by default
        assert "defer" in html

    def test_multi_entry_page_renders_both_bundles(self):
        """GET /multi/ should include both application and admin JS."""
        with _apply_settings():
            from django_rspack.conf import reset_config
            from django_rspack.manifest import reset_manifest

            reset_config()
            reset_manifest()

            client = Client()
            response = client.get("/multi/")

        assert response.status_code == 200
        html = response.content.decode()

        # Application chunks
        assert "/packs/application-1a2b3c.js" in html
        # Admin chunks
        assert "/packs/admin-7g8h9i.js" in html

    def test_asset_path_returns_plain_path(self):
        """GET /asset-path/ should return just the fingerprinted path."""
        with _apply_settings():
            from django_rspack.conf import reset_config
            from django_rspack.manifest import reset_manifest

            reset_config()
            reset_manifest()

            client = Client()
            response = client.get("/asset-path/")

        assert response.status_code == 200
        assert response.content.decode().strip() == "/packs/application-1a2b3c.js"


# ---------------------------------------------------------------------------
# Middleware integration
# ---------------------------------------------------------------------------
class TestMiddlewareIntegration:
    """Test middleware in the full request pipeline."""

    def test_middleware_passes_through_non_asset_requests(self):
        """Non-asset requests should reach the view unchanged."""
        with _apply_settings():
            from django_rspack.conf import reset_config
            from django_rspack.manifest import reset_manifest

            reset_config()
            reset_manifest()

            client = Client()
            response = client.get("/")

        # The view should handle the request, not the middleware
        assert response.status_code == 200

    def test_middleware_skips_when_dev_server_not_running(self):
        """Asset requests should fall through when dev server isn't running."""
        with _apply_settings():
            from django_rspack.conf import reset_config
            from django_rspack.manifest import reset_manifest

            reset_config()
            reset_manifest()

            client = Client()
            # Request an asset path — dev server isn't running, so this falls
            # through to Django's normal handling (404 since no static file)
            response = client.get("/packs/application-1a2b3c.js")

        # Should be 404 since there's no actual file, but NOT a proxy error
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Manifest ↔ Config integration
# ---------------------------------------------------------------------------
class TestManifestConfigIntegration:
    """Test the manifest reads from the path configured in settings."""

    def test_manifest_reads_from_configured_path(self):
        """Manifest should read from the path in RSPACK settings."""
        with _apply_settings():
            from django_rspack.conf import get_config, reset_config
            from django_rspack.manifest import Manifest, reset_manifest

            reset_config()
            reset_manifest()

            config = get_config()
            manifest = Manifest(config=config)

            # Should find everything from our fixture manifest.json
            assert manifest.lookup("application.js") == "/packs/application-1a2b3c.js"
            assert manifest.lookup("application.css") == "/packs/application-4d5e6f.css"
            assert manifest.lookup("admin.js") == "/packs/admin-7g8h9i.js"

    def test_manifest_chunk_lookup_through_config(self):
        """Entry point chunk resolution should work end-to-end."""
        with _apply_settings():
            from django_rspack.conf import get_config, reset_config
            from django_rspack.manifest import Manifest, reset_manifest

            reset_config()
            reset_manifest()

            config = get_config()
            manifest = Manifest(config=config)

            chunks = manifest.lookup_pack_with_chunks("application", pack_type="js")
            assert chunks is not None
            assert len(chunks) == 3
            assert "/packs/runtime-aaa111.js" in chunks
            assert "/packs/vendors-bbb222.js" in chunks
            assert "/packs/application-1a2b3c.js" in chunks

    def test_manifest_update_reflected_in_dev(self):
        """In development (cache_manifest=False), manifest changes should be picked up."""
        with _apply_settings():
            from django_rspack.conf import get_config, reset_config
            from django_rspack.manifest import Manifest, reset_manifest

            reset_config()
            reset_manifest()

            config = get_config()
            manifest = Manifest(config=config)

            # Initial value
            assert manifest.lookup("application.js") == "/packs/application-1a2b3c.js"

            # Modify the manifest on disk
            new_data = {**MANIFEST_DATA, "application.js": "/packs/application-UPDATED.js"}
            config.manifest_path.write_text(json.dumps(new_data))

            # Should see the new value (dev mode, no caching)
            assert manifest.lookup("application.js") == "/packs/application-UPDATED.js"

            # Restore original for other tests
            config.manifest_path.write_text(json.dumps(MANIFEST_DATA))
