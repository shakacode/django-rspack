"""
Management command to compile Rspack assets.

Usage:
    python manage.py rspack_compile
"""

from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

from django_rspack.compiler import compile_assets
from django_rspack.conf import get_config


class Command(BaseCommand):
    help = "Compile Rspack assets for production"

    def handle(self, *args: object, **options: object) -> None:
        config = get_config()
        self.stdout.write(f"Compiling Rspack assets (env: {config.env})...")

        success = compile_assets(config)
        if success:
            self.stdout.write(self.style.SUCCESS("Rspack compilation completed successfully."))
        else:
            self.stderr.write(self.style.ERROR("Rspack compilation failed."))
            sys.exit(1)
