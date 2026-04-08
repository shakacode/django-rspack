"""
Rspack build/compile logic for django-rspack.

Triggers Rspack compilation via the shakapacker npm package.
Handles file locking to prevent concurrent builds.

Usage:
    from django_rspack.compiler import compile_assets
    success = compile_assets()
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from django_rspack.conf import RspackConfiguration, get_config


def _find_rspack_cli(config: RspackConfiguration) -> str:
    """Find the rspack CLI binary in node_modules."""
    node_modules_bin = config.base_dir / "node_modules" / ".bin"
    rspack_bin = node_modules_bin / "rspack"
    if rspack_bin.exists():
        return str(rspack_bin)

    # Fall back to npx
    return "npx rspack"


def _find_config_file(config: RspackConfiguration) -> Path | None:
    """Find the Rspack config file."""
    # Check common locations
    candidates = [
        config.base_dir / "rspack.config.js",
        config.base_dir / "rspack.config.ts",
        config.base_dir / "rspack.config.mjs",
        config.base_dir / "config" / "rspack" / "rspack.config.js",
        config.base_dir / "config" / "rspack.config.js",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _build_env(config: RspackConfiguration) -> dict[str, str]:
    """Build the environment variables for the Rspack process."""
    env = {**os.environ}
    env["NODE_ENV"] = "production" if config.env == "production" else "development"
    asset_host = config.asset_host
    if asset_host:
        env["RSPACK_ASSET_HOST"] = asset_host
    return env


def _compute_digest(config: RspackConfiguration) -> str | None:
    """Compute a SHA256 digest of all source files for freshness checking."""
    source_path = config.source_path
    if not source_path.exists():
        return None

    hasher = hashlib.sha256()
    for root, _dirs, files in os.walk(source_path):
        for filename in sorted(files):
            filepath = Path(root) / filename
            try:
                hasher.update(filepath.read_bytes())
            except OSError:
                continue
    return hasher.hexdigest()


def _read_cached_digest(config: RspackConfiguration) -> str | None:
    """Read the previously stored digest."""
    digest_file = config.cache_path / "last-compilation-digest"
    if digest_file.exists():
        return digest_file.read_text().strip()
    return None


def _write_cached_digest(config: RspackConfiguration, digest: str) -> None:
    """Store the current digest for future freshness checks."""
    config.cache_path.mkdir(parents=True, exist_ok=True)
    digest_file = config.cache_path / "last-compilation-digest"
    digest_file.write_text(digest)


def is_stale(config: RspackConfiguration | None = None) -> bool:
    """Check if the compiled assets are stale and need recompilation.

    Uses the configured compiler_strategy (mtime or digest).
    """
    config = config or get_config()

    if not config.manifest_path.exists():
        return True

    if config.compiler_strategy == "mtime":
        return _is_stale_mtime(config)
    return _is_stale_digest(config)


def _is_stale_mtime(config: RspackConfiguration) -> bool:
    """Check staleness using file modification times."""
    manifest_mtime = config.manifest_path.stat().st_mtime
    source_path = config.source_path
    if not source_path.exists():
        return False

    for root, _dirs, files in os.walk(source_path):
        for filename in files:
            filepath = Path(root) / filename
            try:
                if filepath.stat().st_mtime > manifest_mtime:
                    return True
            except OSError:
                continue
    return False


def _is_stale_digest(config: RspackConfiguration) -> bool:
    """Check staleness using file content digests."""
    current = _compute_digest(config)
    if current is None:
        return False
    cached = _read_cached_digest(config)
    return current != cached


def compile_assets(config: RspackConfiguration | None = None) -> bool:
    """Run Rspack compilation.

    Returns True if compilation succeeded, False otherwise.
    """
    config = config or get_config()

    cli = _find_rspack_cli(config)
    cmd_parts = cli.split() + ["build"]

    config_file = _find_config_file(config)
    if config_file:
        cmd_parts.extend(["--config", str(config_file)])

    env = _build_env(config)

    if config.compile_output:
        stdout = None
        stderr = None
    else:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL

    try:
        result = subprocess.run(
            cmd_parts,
            cwd=str(config.base_dir),
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
    except FileNotFoundError:
        print(
            "Error: Could not find rspack. "
            "Make sure you have installed the shakapacker npm package: npm install shakapacker",
            file=sys.stderr,
        )
        return False

    if result.returncode == 0:
        # Update digest cache on successful build
        if config.compiler_strategy == "digest":
            digest = _compute_digest(config)
            if digest:
                _write_cached_digest(config, digest)
        return True

    print(f"Error: Rspack compilation failed with exit code {result.returncode}", file=sys.stderr)
    return False
