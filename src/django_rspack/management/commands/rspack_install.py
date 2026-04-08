"""
Management command to scaffold Rspack configuration files and setup.

Usage:
    python manage.py rspack_install
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from django_rspack.conf import get_config

DEFAULT_RSPACK_CONFIG = """\
// rspack.config.js
// See https://rspack.dev/config/ for configuration options

const path = require("path");

module.exports = {
  mode: process.env.NODE_ENV === "production" ? "production" : "development",
  entry: {
    application: path.resolve(__dirname, "app/javascript/packs/application.js"),
  },
  output: {
    path: path.resolve(__dirname, "public/packs"),
    publicPath: "/packs/",
    filename: "[name]-[contenthash].js",
  },
  module: {
    rules: [
      {
        test: /\\.css$/,
        use: ["style-loader", "css-loader"],
        type: "javascript/auto",
      },
      {
        test: /\\.(png|jpe?g|gif|svg|ico)$/i,
        type: "asset/resource",
      },
    ],
  },
  plugins: [
    new (require("@rspack/core").HtmlRspackPlugin)({
      template: false,
    }),
  ],
  devServer: {
    port: 3035,
    host: "localhost",
  },
  // Generate manifest.json for django-rspack asset resolution
  experiments: {
    rspackFuture: {
      bundlerInfo: { force: false },
    },
  },
};
"""

DEFAULT_APPLICATION_JS = """\
// Entry point for your application's JavaScript
// This file is compiled by Rspack and referenced with:
//   {% load rspack %}
//   {% rspack_bundle_js "application" %}

console.log("Hello from django-rspack!");
"""

DEFAULT_SHAKAPACKER_YML = """\
# Configuration for django-rspack
# See https://github.com/shakacode/django-rspack for documentation

default: &default
  source_path: app/javascript
  source_entry_path: packs
  nested_entries: true
  public_root_path: public
  public_output_path: packs
  cache_path: tmp/rspack
  compile_output: true
  cache_manifest: false
  additional_paths: []

  dev_server:
    host: localhost
    port: 3035
    server: http
    hmr: false
    inline_css: true
    compress: true

development:
  <<: *default
  compile: true
  compiler_strategy: mtime
  useContentHash: false

test:
  <<: *default
  compile: true
  public_output_path: packs-test

production:
  <<: *default
  compile: false
  cache_manifest: true
  compiler_strategy: digest
  useContentHash: true
"""

PACKAGE_JSON_TEMPLATE = """\
{
  "name": "app",
  "private": true,
  "scripts": {
    "build": "rspack build",
    "dev": "rspack serve"
  },
  "dependencies": {
    "shakapacker": "^9.0.0"
  },
  "devDependencies": {
    "@rspack/cli": "^1.0.0",
    "@rspack/core": "^1.0.0"
  }
}
"""


class Command(BaseCommand):
    help = "Install Rspack configuration files and directory structure"

    def add_arguments(self, parser: object) -> None:
        parser.add_argument(  # type: ignore[attr-defined]
            "--force",
            action="store_true",
            help="Overwrite existing files",
        )

    def handle(self, *args: object, **options: object) -> None:
        config = get_config()
        base_dir = config.base_dir
        force = options.get("force", False)

        self.stdout.write("Installing django-rspack...")

        # Create directory structure
        self._create_directories(config)

        # Create config files
        self._write_file(
            base_dir / "config" / "shakapacker.yml",
            DEFAULT_SHAKAPACKER_YML,
            force=force,
        )
        self._write_file(
            base_dir / "rspack.config.js",
            DEFAULT_RSPACK_CONFIG,
            force=force,
        )
        self._write_file(
            base_dir / "app" / "javascript" / "packs" / "application.js",
            DEFAULT_APPLICATION_JS,
            force=force,
        )

        # Create package.json if it doesn't exist
        package_json = base_dir / "package.json"
        if not package_json.exists() or force:
            self._write_file(package_json, PACKAGE_JSON_TEMPLATE, force=force)

        # Update .gitignore
        self._update_gitignore(base_dir)

        self.stdout.write(self.style.SUCCESS("\ndjango-rspack installed successfully!"))
        self.stdout.write("\nNext steps:")
        self.stdout.write("  1. Run: npm install")
        self.stdout.write("  2. Add 'django_rspack' to INSTALLED_APPS in settings.py")
        self.stdout.write("  3. Add template tags to your templates:")
        self.stdout.write('     {% load rspack %}')
        self.stdout.write('     {% rspack_bundle_js "application" %}')
        self.stdout.write("  4. Start the dev server: python manage.py rspack_dev_server")

    def _create_directories(self, config: object) -> None:
        """Create the required directory structure."""
        dirs = [
            config.source_entry_path,  # type: ignore[attr-defined]
            config.public_output_path,  # type: ignore[attr-defined]
            config.cache_path,  # type: ignore[attr-defined]
            config.base_dir / "config",  # type: ignore[attr-defined]
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  Created directory: {d}")

    def _write_file(self, path: Path, content: str, force: bool = False) -> None:
        """Write a file, warning if it already exists."""
        if path.exists() and not force:
            self.stdout.write(f"  Skipped (already exists): {path}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.stdout.write(f"  Created: {path}")

    def _update_gitignore(self, base_dir: Path) -> None:
        """Add Rspack output paths to .gitignore."""
        gitignore = base_dir / ".gitignore"
        entries = [
            "/public/packs",
            "/public/packs-test",
            "/tmp/rspack",
            "/node_modules",
        ]

        existing = ""
        if gitignore.exists():
            existing = gitignore.read_text()

        additions = []
        for entry in entries:
            if entry not in existing:
                additions.append(entry)

        if additions:
            with open(gitignore, "a") as f:
                f.write("\n# django-rspack\n")
                for entry in additions:
                    f.write(f"{entry}\n")
            self.stdout.write(f"  Updated .gitignore with {len(additions)} entries")
