"""
Minimal Django project for integration/regression testing.

This is a real Django project that can be booted and exercised
end-to-end, catching wiring issues that isolated unit tests miss:
- App loading and ready() hook
- Template tag discovery and registration
- Management command discovery
- Middleware ordering
- URL routing through views that render templates
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from django.http import HttpResponse
from django.template import engines
from django.urls import path

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
_BASE = Path(tempfile.mkdtemp(prefix="djrspack_test_"))

# Pre-create the directory structure so the app can boot cleanly
(_BASE / "public" / "packs").mkdir(parents=True, exist_ok=True)
(_BASE / "app" / "javascript" / "packs").mkdir(parents=True, exist_ok=True)

# Write a realistic manifest.json
MANIFEST_DATA = {
    "application.js": "/packs/application-1a2b3c.js",
    "application.css": "/packs/application-4d5e6f.css",
    "admin.js": "/packs/admin-7g8h9i.js",
    "entrypoints": {
        "application": {
            "assets": {
                "js": [
                    "/packs/runtime-aaa111.js",
                    "/packs/vendors-bbb222.js",
                    "/packs/application-1a2b3c.js",
                ],
                "css": [
                    "/packs/application-4d5e6f.css",
                ],
            }
        },
        "admin": {
            "assets": {
                "js": ["/packs/admin-7g8h9i.js"],
            }
        },
    },
}
(_BASE / "public" / "packs" / "manifest.json").write_text(json.dumps(MANIFEST_DATA))


TESTAPP_SETTINGS = {
    "BASE_DIR": str(_BASE),
    "SECRET_KEY": "integration-test-key-not-for-production",
    "DEBUG": True,
    "ALLOWED_HOSTS": ["*"],
    "INSTALLED_APPS": [
        "django.contrib.contenttypes",
        "django.contrib.staticfiles",
        "django_rspack",
    ],
    "MIDDLEWARE": [
        "django_rspack.middleware.RspackDevServerMiddleware",
    ],
    "TEMPLATES": [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [str(Path(__file__).parent / "testapp" / "templates")],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                ],
            },
        },
    ],
    "STATIC_URL": "/static/",
    "ROOT_URLCONF": "tests.testapp_settings",
    "RSPACK": {
        "source_path": "app/javascript",
        "source_entry_path": "packs",
        "public_root_path": "public",
        "public_output_path": "packs",
    },
}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def index_view(request: object) -> HttpResponse:
    engine = engines["django"]
    template = engine.from_string(
        '{% load rspack %}'
        '<html><head>{% rspack_bundle_css "application" %}</head>'
        '<body>{% rspack_bundle_js "application" %}</body></html>'
    )
    return HttpResponse(template.render({}, request))  # type: ignore[arg-type]


def multi_entry_view(request: object) -> HttpResponse:
    engine = engines["django"]
    template = engine.from_string(
        '{% load rspack %}'
        '<html><head>{% rspack_bundle_css "application" %}</head>'
        '<body>'
        '{% rspack_bundle_js "application" %}'
        '{% rspack_bundle_js "admin" %}'
        '</body></html>'
    )
    return HttpResponse(template.render({}, request))  # type: ignore[arg-type]


def asset_path_view(request: object) -> HttpResponse:
    engine = engines["django"]
    template = engine.from_string(
        '{% load rspack %}{% rspack_asset_path "application.js" %}'
    )
    return HttpResponse(template.render({}, request))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
urlpatterns = [
    path("", index_view, name="index"),
    path("multi/", multi_entry_view, name="multi"),
    path("asset-path/", asset_path_view, name="asset-path"),
]
