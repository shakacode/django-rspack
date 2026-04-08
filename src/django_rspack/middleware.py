"""
Dev server proxy middleware for django-rspack.

In development, proxies requests for Rspack-compiled assets to the
running Rspack dev server instead of serving from disk.

Add to MIDDLEWARE in settings.py:
    MIDDLEWARE = [
        "django_rspack.middleware.RspackDevServerMiddleware",
        ...
    ]
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import requests
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound

from django_rspack.conf import get_config
from django_rspack.dev_server import is_running

logger = logging.getLogger(__name__)


class RspackDevServerMiddleware:
    """Proxy middleware that forwards asset requests to the Rspack dev server.

    Only active when:
    - DEBUG is True (development mode)
    - The dev server is running

    Requests matching the public output path (e.g., /packs/) are proxied
    to the dev server. All other requests pass through normally.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        config = get_config()

        # Only proxy in development
        if config.env != "development":
            return self.get_response(request)

        # Check if this is an asset request
        output_path = "/" + config.public_output_path.relative_to(config.public_root_path).as_posix() + "/"
        if not request.path.startswith(output_path):
            return self.get_response(request)

        # Only proxy if dev server is running
        if not is_running(config):
            return self.get_response(request)

        return self._proxy_to_dev_server(request, config)

    def _proxy_to_dev_server(self, request: HttpRequest, config: object) -> HttpResponse:
        """Forward the request to the Rspack dev server."""
        dev_url = f"{config.dev_server_url}{request.path}"  # type: ignore[attr-defined]

        try:
            proxied = requests.get(dev_url, timeout=30, stream=True)
        except requests.ConnectionError:
            logger.warning("Rspack dev server connection failed for %s", request.path)
            return self.get_response(request)
        except requests.Timeout:
            logger.warning("Rspack dev server timed out for %s", request.path)
            return self.get_response(request)

        if proxied.status_code == 404:
            return HttpResponseNotFound()

        response = HttpResponse(
            content=proxied.content,
            status=proxied.status_code,
            content_type=proxied.headers.get("Content-Type", "application/octet-stream"),
        )

        # Forward relevant headers from the dev server
        for header in ("Cache-Control", "ETag", "Last-Modified", "Content-Encoding"):
            if header in proxied.headers:
                response[header] = proxied.headers[header]

        return response
