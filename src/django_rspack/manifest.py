"""
Manifest reader for django-rspack.

Reads the manifest.json file produced by Rspack and resolves pack names
to their fingerprinted output paths. Supports caching in production
and auto-reloading in development.

Usage:
    from django_rspack.manifest import get_manifest
    manifest = get_manifest()
    manifest.lookup("application.js")
    # => "/packs/application-abc123.js"
"""

from __future__ import annotations

import json
import os
from typing import Any

from django_rspack.conf import get_config


class MissingEntryError(Exception):
    """Raised when a requested asset cannot be found in the manifest."""


class Manifest:
    """Reads and caches the Rspack manifest.json file.

    In production (cache_manifest=True), the manifest is read once and cached.
    In development (cache_manifest=False), the manifest is re-read on every lookup.
    """

    def __init__(self, config: Any | None = None) -> None:
        self._config = config or get_config()
        self._data: dict[str, Any] | None = None
        self._manifest_existed: bool | None = None

    def refresh(self) -> dict[str, Any]:
        """Force reload the manifest from disk."""
        self._data, self._manifest_existed = self._load()
        return self._data

    @property
    def data(self) -> dict[str, Any]:
        """Return the manifest data, loading/caching as appropriate."""
        if self._config.cache_manifest and self._data is not None:
            return self._data
        self._data, self._manifest_existed = self._load()
        return self._data

    def lookup(self, name: str, pack_type: str | None = None) -> str | None:
        """Look up the compiled path for an asset.

        Args:
            name: The source file name (e.g., "application.js" or "application").
            pack_type: Optional type hint ("js", "css"). If not provided,
                       the extension from the name is used.

        Returns:
            The compiled asset path, or None if not found.
        """
        full_name = self._full_pack_name(name, pack_type)
        entry = self._find(full_name)
        return entry

    def lookup_strict(self, name: str, pack_type: str | None = None) -> str:
        """Like lookup(), but raises MissingEntryError if the asset is not found."""
        result = self.lookup(name, pack_type)
        if result is None:
            self._handle_missing_entry(name, pack_type)
        return result  # type: ignore[return-value]

    def lookup_pack_with_chunks(self, name: str, pack_type: str | None = None) -> list[str] | None:
        """Look up all chunks for an entry point (including split code).

        Args:
            name: The entry point name (e.g., "application").
            pack_type: The asset type ("js" or "css").

        Returns:
            A list of asset paths for all chunks, or None if not found.
        """
        manifest_type = self._manifest_type(pack_type)
        manifest_name = self._manifest_name(name, manifest_type)

        entrypoints = self._find("entrypoints")
        if not isinstance(entrypoints, dict):
            return None

        entry = entrypoints.get(manifest_name)
        if not isinstance(entry, dict):
            return None

        assets = entry.get("assets")
        if not isinstance(assets, dict):
            return None

        return assets.get(manifest_type)

    def lookup_pack_with_chunks_strict(self, name: str, pack_type: str | None = None) -> list[str]:
        """Like lookup_pack_with_chunks(), but raises MissingEntryError if not found."""
        result = self.lookup_pack_with_chunks(name, pack_type)
        if result is None:
            self._handle_missing_entry(name, pack_type)
        return result  # type: ignore[return-value]

    def _load(self) -> tuple[dict[str, Any], bool]:
        """Load and parse the manifest.json file."""
        manifest_path = self._config.manifest_path
        if manifest_path.exists():
            contents = manifest_path.read_text().strip()
            if not contents:
                return {}, True
            try:
                return json.loads(contents), True
            except json.JSONDecodeError:
                return {}, True
        return {}, False

    def _find(self, name: str) -> Any | None:
        """Find a key in the manifest data."""
        value = self.data.get(name)
        if value is None:
            return None

        # If the value is a dict with a "src" key, return that
        if isinstance(value, dict) and "src" in value:
            return value["src"]

        return value

    def _full_pack_name(self, name: str, pack_type: str | None) -> str:
        """Build full pack name with extension if not already present."""
        name = str(name)
        if os.path.splitext(name)[1]:
            return name
        ext = self._manifest_type(pack_type)
        if ext:
            return f"{name}.{ext}"
        return name

    def _manifest_type(self, pack_type: str | None) -> str:
        """Normalize pack type to file extension."""
        if pack_type == "javascript":
            return "js"
        if pack_type == "stylesheet":
            return "css"
        return pack_type or ""

    def _manifest_name(self, name: str, pack_type: str) -> str:
        """Strip the extension from the name for entrypoint lookups."""
        if pack_type and name.endswith(f".{pack_type}"):
            return name[: -len(pack_type) - 1]
        return name

    def _handle_missing_entry(self, name: str, pack_type: str | None) -> None:
        """Raise a descriptive MissingEntryError."""
        full_name = self._full_pack_name(name, pack_type)
        manifest_path = self._config.manifest_path

        if not self.data:
            if self._manifest_existed:
                raise MissingEntryError(
                    f"Rspack manifest is empty at {manifest_path}. "
                    f"Rspack is likely still compiling.\n\n"
                    f"This typically happens when:\n"
                    f"1. You just started the dev server and it's still compiling\n"
                    f"2. The dev server crashed during startup\n"
                    f"3. Rspack compilation hasn't completed yet\n\n"
                    f"What to do:\n"
                    f"- Wait a few seconds and refresh the page\n"
                    f"- Check your terminal for Rspack build progress\n"
                    f"- Look for errors in the Rspack output"
                )
            raise MissingEntryError(
                f"Rspack manifest file not found at {manifest_path}.\n\n"
                f"This typically happens when:\n"
                f"1. You haven't started the dev server yet\n"
                f"2. The compile process hasn't created the manifest file\n"
                f"3. The manifest_path configuration is incorrect\n\n"
                f"What to do:\n"
                f"- Start the dev server: python manage.py rspack_dev_server\n"
                f"- Or run a manual build: python manage.py rspack_compile\n"
                f"- Verify manifest_path in your configuration"
            )

        # Manifest exists but entry not found
        manifest_keys = json.dumps(list(self.data.keys()), indent=2)
        raise MissingEntryError(
            f"Can't find {full_name} in {manifest_path}. Possible causes:\n"
            f"1. You forgot to install JavaScript packages (npm install)\n"
            f"2. Your app has code with a non-standard extension that isn't configured\n"
            f"3. You have set compile: false for this environment\n"
            f"4. Rspack has not yet finished running to reflect updates\n"
            f"5. Your Rspack configuration is not creating a manifest with the expected structure\n\n"
            f"Your manifest contains these keys:\n{manifest_keys}"
        )


# Module-level cached manifest accessor
_manifest: Manifest | None = None


def get_manifest() -> Manifest:
    """Get the global Manifest instance."""
    global _manifest
    if _manifest is None:
        _manifest = Manifest()
    return _manifest


def reset_manifest() -> None:
    """Reset the cached manifest. Primarily for testing."""
    global _manifest
    _manifest = None
