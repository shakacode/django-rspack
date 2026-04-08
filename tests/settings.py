"""Minimal Django settings for testing django-rspack."""

import tempfile
from pathlib import Path

BASE_DIR = Path(tempfile.mkdtemp())

SECRET_KEY = "test-secret-key-not-for-production"

DEBUG = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django_rspack",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

STATIC_URL = "/static/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# django-rspack config for tests
RSPACK = {
    "source_path": "app/javascript",
    "source_entry_path": "packs",
    "public_root_path": "public",
    "public_output_path": "packs",
}
