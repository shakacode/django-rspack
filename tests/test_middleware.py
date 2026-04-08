"""Tests for django_rspack.middleware."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from django_rspack.conf import reset_config
from django_rspack.manifest import reset_manifest
from django_rspack.middleware import RspackDevServerMiddleware


class TestMiddleware:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_project, settings, sample_manifest_data):
        reset_config()
        reset_manifest()
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        (tmp_project / "public" / "packs" / "manifest.json").write_text(
            json.dumps(sample_manifest_data)
        )

    @pytest.fixture
    def get_response(self):
        """Mock get_response that returns a 200."""
        response = MagicMock()
        response.status_code = 200
        return MagicMock(return_value=response)

    @pytest.fixture
    def middleware(self, get_response):
        return RspackDevServerMiddleware(get_response)

    @pytest.fixture
    def rf(self):
        return RequestFactory()

    def test_non_asset_request_passes_through(self, middleware, get_response, rf):
        """Non-asset requests should pass through to Django."""
        request = rf.get("/about/")
        middleware(request)
        get_response.assert_called_once_with(request)

    def test_asset_request_without_dev_server(self, middleware, get_response, rf):
        """Asset requests should pass through when dev server is not running."""
        request = rf.get("/packs/application-abc123.js")
        with patch("django_rspack.middleware.is_running", return_value=False):
            middleware(request)
        get_response.assert_called_once_with(request)

    @patch("django_rspack.middleware.is_running", return_value=True)
    @patch("django_rspack.middleware.requests.get")
    def test_asset_request_proxied_to_dev_server(self, mock_get, mock_running, middleware, rf):
        """Asset requests should be proxied when dev server is running."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"console.log('hello');"
        mock_response.headers = {"Content-Type": "application/javascript"}
        mock_get.return_value = mock_response

        request = rf.get("/packs/application-abc123.js")
        response = middleware(request)

        assert response.status_code == 200
        assert response.content == b"console.log('hello');"
        mock_get.assert_called_once()

    @patch("django_rspack.middleware.is_running", return_value=True)
    @patch("django_rspack.middleware.requests.get")
    def test_proxy_404(self, mock_get, mock_running, middleware, rf):
        """Should return 404 when dev server returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        request = rf.get("/packs/nonexistent.js")
        response = middleware(request)

        assert response.status_code == 404

    @patch("django_rspack.middleware.is_running", return_value=True)
    @patch("django_rspack.middleware.requests.get")
    def test_proxy_connection_error_falls_through(self, mock_get, mock_running, middleware, get_response, rf):
        """Should fall through to Django when proxy connection fails."""
        import requests as req_lib

        mock_get.side_effect = req_lib.ConnectionError()

        request = rf.get("/packs/application-abc123.js")
        middleware(request)
        get_response.assert_called_once_with(request)

    def test_production_mode_skips_proxy(self, tmp_project, settings, rf):
        """Middleware should not proxy in production mode."""
        reset_config()
        settings.DEBUG = False
        settings.RSPACK = {}

        get_response = MagicMock(return_value=MagicMock(status_code=200))
        mw = RspackDevServerMiddleware(get_response)

        request = rf.get("/packs/application-abc123.js")
        mw(request)
        get_response.assert_called_once_with(request)
