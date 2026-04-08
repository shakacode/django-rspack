"""
Dev server status and process management for django-rspack.

Checks whether the Rspack dev server is running and provides
connection information.

Usage:
    from django_rspack.dev_server import is_running, get_dev_server_url
    if is_running():
        url = get_dev_server_url()
"""

from __future__ import annotations

import socket

from django_rspack.conf import RspackConfiguration, get_config

# Default timeout for checking dev server connectivity (seconds)
CONNECT_TIMEOUT = 0.1


def is_running(config: RspackConfiguration | None = None) -> bool:
    """Check if the Rspack dev server is running.

    Attempts a TCP connection to the configured host and port.
    Returns True if the connection succeeds, False otherwise.
    """
    config = config or get_config()

    if not config.dev_server:
        return False

    host = config.dev_server_host
    port = config.dev_server_port

    try:
        sock = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        sock.close()
        return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


def get_dev_server_url(config: RspackConfiguration | None = None) -> str:
    """Get the full URL for the dev server."""
    config = config or get_config()
    return config.dev_server_url


def get_dev_server_host(config: RspackConfiguration | None = None) -> str:
    """Get the dev server host."""
    config = config or get_config()
    return config.dev_server_host


def get_dev_server_port(config: RspackConfiguration | None = None) -> int:
    """Get the dev server port."""
    config = config or get_config()
    return config.dev_server_port
