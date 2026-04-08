"""
Django template tags for including Rspack-compiled assets.

Usage in templates:
    {% load rspack %}

    {% rspack_bundle_js "application" %}
    <!-- outputs: <script src="/packs/application-abc123.js" defer></script> -->

    {% rspack_bundle_css "application" %}
    <!-- outputs: <link rel="stylesheet" href="/packs/application-abc123.css" /> -->

    {% rspack_bundle "application" "js" %}
    <!-- same as rspack_bundle_js -->

    {% rspack_asset_path "application.js" %}
    <!-- outputs the path only: /packs/application-abc123.js -->
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from django_rspack.conf import get_config
from django_rspack.manifest import Manifest, get_manifest

register = template.Library()


def _build_asset_url(path: str) -> str:
    """Prepend asset host to a path if configured."""
    config = get_config()
    asset_host = config.asset_host
    if asset_host:
        host = asset_host.rstrip("/")
        return f"{host}{path}"
    return path


def _render_js_tags(
    manifest: Manifest,
    name: str,
    attrs: dict[str, str | bool],
) -> str:
    """Render <script> tag(s) for a JavaScript entry point."""
    config = get_config()

    # Try chunk-based lookup first (handles code splitting)
    chunks = manifest.lookup_pack_with_chunks(name, pack_type="js")
    if chunks:
        paths = chunks
    else:
        # Fall back to single-file lookup
        path = manifest.lookup_strict(name, pack_type="js")
        paths = [path]

    tags = []
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        url = _build_asset_url(path)
        attr_str = _build_attr_str(attrs, config, path)
        tags.append(f'<script src="{url}"{attr_str}></script>')

    return "\n".join(tags)


def _render_css_tags(
    manifest: Manifest,
    name: str,
    attrs: dict[str, str | bool],
) -> str:
    """Render <link> tag(s) for a CSS entry point."""
    config = get_config()

    # Try chunk-based lookup first
    chunks = manifest.lookup_pack_with_chunks(name, pack_type="css")
    if chunks:
        paths = chunks
    else:
        path = manifest.lookup_strict(name, pack_type="css")
        paths = [path]

    tags = []
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        url = _build_asset_url(path)
        attr_str = _build_attr_str(attrs, config, path)
        tags.append(f'<link rel="stylesheet" href="{url}"{attr_str} />')

    return "\n".join(tags)


def _build_attr_str(attrs: dict[str, str | bool], config: object, path: str) -> str:
    """Build the HTML attribute string for a tag."""
    parts: list[str] = []
    for key, value in attrs.items():
        if isinstance(value, bool):
            if value:
                parts.append(f" {key}")
        else:
            parts.append(f' {key}="{value}"')

    # Add integrity attributes if enabled
    if getattr(config, "integrity_enabled", False):
        cross_origin = getattr(config, "integrity_cross_origin", "anonymous")
        parts.append(f' crossorigin="{cross_origin}"')

    return "".join(parts)


@register.simple_tag
def rspack_bundle_js(name: str, **kwargs: str | bool) -> str:
    """Render <script> tags for an Rspack JavaScript entry point.

    Usage:
        {% rspack_bundle_js "application" %}
        {% rspack_bundle_js "application" defer=True %}
        {% rspack_bundle_js "application" async=True %}
    """
    attrs: dict[str, str | bool] = {}
    # Default to defer unless explicitly overridden
    defer = kwargs.pop("defer", True)
    async_attr = kwargs.pop("async", False)
    if defer:
        attrs["defer"] = True
    if async_attr:
        attrs["async"] = True
    attrs.update(kwargs)

    manifest = get_manifest()
    html = _render_js_tags(manifest, name, attrs)
    return mark_safe(html)


@register.simple_tag
def rspack_bundle_css(name: str, **kwargs: str | bool) -> str:
    """Render <link> tags for an Rspack CSS entry point.

    Usage:
        {% rspack_bundle_css "application" %}
        {% rspack_bundle_css "application" media="print" %}
    """
    manifest = get_manifest()
    html = _render_css_tags(manifest, name, dict(kwargs))
    return mark_safe(html)


@register.simple_tag
def rspack_bundle(name: str, bundle_type: str, **kwargs: str | bool) -> str:
    """Render tags for an Rspack entry point of the specified type.

    Usage:
        {% rspack_bundle "application" "js" %}
        {% rspack_bundle "application" "css" %}
    """
    manifest = get_manifest()
    if bundle_type == "js":
        attrs: dict[str, str | bool] = {"defer": True}
        attrs.update(kwargs)
        html = _render_js_tags(manifest, name, attrs)
    elif bundle_type == "css":
        html = _render_css_tags(manifest, name, dict(kwargs))
    else:
        raise template.TemplateSyntaxError(f'rspack_bundle type must be "js" or "css", got "{bundle_type}"')
    return mark_safe(html)


@register.simple_tag
def rspack_asset_path(name: str) -> str:
    """Return the compiled asset path (without HTML tags).

    Usage:
        {% rspack_asset_path "application.js" %}
        <!-- outputs: /packs/application-abc123.js -->
    """
    manifest = get_manifest()
    path = manifest.lookup_strict(name)
    return _build_asset_url(path)


@register.simple_tag
def rspack_asset_url(name: str) -> str:
    """Return the full URL for a compiled asset.

    Usage:
        {% rspack_asset_url "application.js" %}
        <!-- outputs: https://cdn.example.com/packs/application-abc123.js -->
    """
    manifest = get_manifest()
    path = manifest.lookup_strict(name)
    return _build_asset_url(path)
