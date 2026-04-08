"""
Configuration management for django-rspack.

Loads settings from Django settings (RSPACK dict) and/or shakapacker.yml,
with Django settings taking precedence.

Usage:
    from django_rspack.conf import get_config
    config = get_config()
    config.manifest_path  # => Path to manifest.json
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings


def _get_default_config() -> dict[str, Any]:
    """Load the bundled default shakapacker.yml."""
    default_path = Path(__file__).parent / "default_config" / "shakapacker.yml"
    with open(default_path) as f:
        return yaml.safe_load(f)


def _get_django_env() -> str:
    """Map Django's DEBUG setting to a Shakapacker environment."""
    env_override = os.environ.get("RSPACK_ENV")
    if env_override:
        return env_override
    if getattr(settings, "DEBUG", False):
        return "development"
    return "production"


def _load_yaml_config(config_path: Path, env: str) -> dict[str, Any]:
    """Load environment-specific config from a YAML file."""
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(
            f"YAML syntax error in {config_path}. "
            f"YAML must be consistently indented using spaces. Tabs are not allowed. "
            f"Error: {e}"
        ) from e

    if not isinstance(data, dict):
        return {}

    # Try environment-specific, fall back to production, then empty
    if env in data:
        return data[env] or {}
    if "production" in data:
        return data["production"] or {}
    return {}


class RspackConfiguration:
    """Holds the resolved configuration for django-rspack.

    Configuration is resolved by merging (in order of precedence):
    1. Django settings (settings.RSPACK dict)
    2. Project's shakapacker.yml (environment-specific section)
    3. Bundled default config
    """

    def __init__(self) -> None:
        self._env = _get_django_env()
        self._base_dir = self._resolve_base_dir()
        self._data = self._load()

    def _resolve_base_dir(self) -> Path:
        """Resolve the project base directory."""
        base = getattr(settings, "BASE_DIR", None)
        if base:
            return Path(base)
        return Path.cwd()

    def _load(self) -> dict[str, Any]:
        """Merge configs: defaults < yaml < django settings."""
        # 1. Bundled defaults for this environment
        defaults_all = _get_default_config()
        defaults = defaults_all.get(self._env) or defaults_all.get("production") or {}

        # 2. Project's shakapacker.yml
        django_settings = getattr(settings, "RSPACK", {}) or {}
        config_path_override = django_settings.get("config_path")
        if config_path_override:
            yaml_path = self._base_dir / config_path_override
        else:
            yaml_path = self._base_dir / "config" / "shakapacker.yml"
        yaml_config = _load_yaml_config(yaml_path, self._env)

        # 3. Merge: defaults < yaml < django settings
        merged = {**defaults, **yaml_config, **django_settings}
        return merged

    @property
    def env(self) -> str:
        return self._env

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @property
    def source_path(self) -> Path:
        return self._base_dir / self._data.get("source_path", "app/javascript")

    @property
    def source_entry_path(self) -> Path:
        entry = self._data.get("source_entry_path", "packs")
        return self.source_path / entry

    @property
    def public_root_path(self) -> Path:
        return self._base_dir / self._data.get("public_root_path", "public")

    @property
    def public_output_path(self) -> Path:
        return self.public_root_path / self._data.get("public_output_path", "packs")

    @property
    def manifest_path(self) -> Path:
        custom = self._data.get("manifest_path")
        if custom:
            return self._base_dir / custom
        return self.public_output_path / "manifest.json"

    @property
    def cache_path(self) -> Path:
        return self._base_dir / self._data.get("cache_path", "tmp/rspack")

    @property
    def compile(self) -> bool:
        return bool(self._data.get("compile", self._env == "development"))

    @property
    def compile_output(self) -> bool:
        # Support both the new name and legacy shakapacker name
        return bool(self._data.get("compile_output", self._data.get("webpack_compile_output", True)))

    @property
    def cache_manifest(self) -> bool:
        return bool(self._data.get("cache_manifest", self._env == "production"))

    @property
    def compiler_strategy(self) -> str:
        return self._data.get("compiler_strategy", "digest")

    @property
    def use_content_hash(self) -> bool:
        return bool(self._data.get("useContentHash", True))

    @property
    def nested_entries(self) -> bool:
        return bool(self._data.get("nested_entries", True))

    @property
    def additional_paths(self) -> list[str]:
        return self._data.get("additional_paths", [])

    @property
    def dev_server(self) -> dict[str, Any]:
        return self._data.get("dev_server", {})

    @property
    def dev_server_host(self) -> str:
        return os.environ.get(
            "RSPACK_DEV_SERVER_HOST",
            str(self.dev_server.get("host", "localhost")),
        )

    @property
    def dev_server_port(self) -> int:
        port_str = os.environ.get("RSPACK_DEV_SERVER_PORT")
        if port_str:
            return int(port_str)
        return int(self.dev_server.get("port", 3035))

    @property
    def dev_server_protocol(self) -> str:
        env_val = os.environ.get("RSPACK_DEV_SERVER_SERVER")
        if env_val and env_val in ("http", "https"):
            return env_val
        server = self.dev_server.get("server", "http")
        if isinstance(server, dict):
            server = server.get("type", "http")
        if server in ("http", "https"):
            return server
        return "http"

    @property
    def dev_server_url(self) -> str:
        return f"{self.dev_server_protocol}://{self.dev_server_host}:{self.dev_server_port}"

    @property
    def dev_server_hmr(self) -> bool:
        return bool(self.dev_server.get("hmr", False))

    @property
    def dev_server_inline_css(self) -> bool:
        val = self.dev_server.get("inline_css", True)
        return val not in (False, "false")

    @property
    def integrity(self) -> dict[str, Any]:
        return self._data.get("integrity", {})

    @property
    def integrity_enabled(self) -> bool:
        return bool(self.integrity.get("enabled", False))

    @property
    def integrity_hash_functions(self) -> list[str]:
        return self.integrity.get("hash_functions", ["sha384"])

    @property
    def integrity_cross_origin(self) -> str:
        return self.integrity.get("cross_origin", "anonymous")

    @property
    def asset_host(self) -> str | None:
        env_host = os.environ.get("RSPACK_ASSET_HOST")
        if env_host:
            return env_host
        return self._data.get("asset_host")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a raw configuration value."""
        return self._data.get(key, default)


# Module-level cached config accessor
_config: RspackConfiguration | None = None


def get_config() -> RspackConfiguration:
    """Get the global RspackConfiguration instance.

    The configuration is created once and cached. Call reset_config()
    to force a reload (useful in tests).
    """
    global _config
    if _config is None:
        _config = RspackConfiguration()
    return _config


def reset_config() -> None:
    """Reset the cached configuration. Primarily for testing."""
    global _config
    _config = None
