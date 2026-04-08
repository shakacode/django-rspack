"""
Management command to start the Rspack dev server.

Usage:
    python manage.py rspack_dev_server
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

from django.core.management.base import BaseCommand

from django_rspack.conf import get_config


class Command(BaseCommand):
    help = "Start the Rspack development server"

    def add_arguments(self, parser: object) -> None:
        parser.add_argument(  # type: ignore[attr-defined]
            "--port",
            type=int,
            help="Port to run the dev server on (overrides config)",
        )
        parser.add_argument(  # type: ignore[attr-defined]
            "--host",
            type=str,
            help="Host to bind the dev server to (overrides config)",
        )

    def handle(self, *args: object, **options: object) -> None:
        config = get_config()

        host = options.get("host") or config.dev_server_host
        port = options.get("port") or config.dev_server_port

        self.stdout.write(f"Starting Rspack dev server on {host}:{port}...")

        cmd = self._build_command(config, host, port)
        env = self._build_env(config)

        try:
            process = subprocess.Popen(cmd, cwd=str(config.base_dir), env=env)

            # Forward signals to the child process
            def signal_handler(signum: int, frame: object) -> None:
                process.send_signal(signum)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            process.wait()
            sys.exit(process.returncode)
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(
                    "Could not find rspack. "
                    "Make sure you have installed the shakapacker npm package:\n"
                    "  npm install shakapacker"
                )
            )
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write("\nStopping Rspack dev server...")
            process.terminate()
            process.wait()

    def _build_command(self, config: object, host: str, port: int) -> list[str]:
        """Build the rspack serve command."""
        node_modules_bin = config.base_dir / "node_modules" / ".bin"  # type: ignore[attr-defined]
        rspack_bin = node_modules_bin / "rspack"

        cmd = [str(rspack_bin)] if rspack_bin.exists() else ["npx", "rspack"]

        cmd.append("serve")
        cmd.extend(["--host", str(host)])
        cmd.extend(["--port", str(port)])

        # Look for config file
        config_file = self._find_config_file(config)
        if config_file:
            cmd.extend(["--config", str(config_file)])

        if config.dev_server_hmr:  # type: ignore[attr-defined]
            cmd.append("--hot")

        return cmd

    def _find_config_file(self, config: object) -> str | None:
        """Find the rspack config file."""
        base = config.base_dir  # type: ignore[attr-defined]
        candidates = [
            base / "rspack.config.js",
            base / "rspack.config.ts",
            base / "rspack.config.mjs",
            base / "config" / "rspack" / "rspack.config.js",
            base / "config" / "rspack.config.js",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def _build_env(self, config: object) -> dict[str, str]:
        """Build environment variables for the dev server process."""
        env = {**os.environ}
        env["NODE_ENV"] = "development"
        return env
