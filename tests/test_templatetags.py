"""Tests for django_rspack template tags."""

from __future__ import annotations

import json

import pytest
from django.template import Context, Template

from django_rspack.conf import reset_config
from django_rspack.manifest import reset_manifest


@pytest.mark.django_db
class TestTemplateTags:
    @pytest.fixture(autouse=True)
    def _setup_manifest(self, tmp_project, settings, sample_manifest_data):
        """Set up a manifest for template tag tests."""
        reset_config()
        reset_manifest()
        settings.BASE_DIR = str(tmp_project)
        settings.DEBUG = True
        settings.RSPACK = {}
        (tmp_project / "public" / "packs").mkdir(parents=True, exist_ok=True)
        manifest_path = tmp_project / "public" / "packs" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest_data))

    def _render(self, template_str: str, context: dict | None = None) -> str:
        """Render a template string and return the output."""
        template = Template(template_str)
        return template.render(Context(context or {})).strip()

    def test_rspack_bundle_js(self):
        """Should render a <script> tag with defer."""
        html = self._render('{% load rspack %}{% rspack_bundle_js "application" %}')
        assert '<script src="/packs/application-abc123.js" defer></script>' in html

    def test_rspack_bundle_js_chunks(self):
        """Should render multiple <script> tags for entry with chunks."""
        html = self._render('{% load rspack %}{% rspack_bundle_js "application" %}')
        assert "/packs/runtime-abc123.js" in html
        assert "/packs/vendor-789xyz.js" in html
        assert "/packs/application-abc123.js" in html
        assert html.count("<script") == 3

    def test_rspack_bundle_css(self):
        """Should render a <link> tag for CSS."""
        html = self._render('{% load rspack %}{% rspack_bundle_css "application" %}')
        assert '<link rel="stylesheet" href="/packs/application-def456.css"' in html

    def test_rspack_bundle_css_chunks(self):
        """Should render CSS chunk tags."""
        html = self._render('{% load rspack %}{% rspack_bundle_css "application" %}')
        assert "/packs/application-def456.css" in html

    def test_rspack_bundle_js_type(self):
        """rspack_bundle with js type should render script tags."""
        html = self._render('{% load rspack %}{% rspack_bundle "application" "js" %}')
        assert "<script" in html
        assert "/packs/application-abc123.js" in html

    def test_rspack_bundle_css_type(self):
        """rspack_bundle with css type should render link tags."""
        html = self._render('{% load rspack %}{% rspack_bundle "application" "css" %}')
        assert '<link rel="stylesheet"' in html
        assert "/packs/application-def456.css" in html

    def test_rspack_asset_path(self):
        """Should return just the asset path."""
        html = self._render('{% load rspack %}{% rspack_asset_path "application.js" %}')
        assert html == "/packs/application-abc123.js"

    def test_rspack_asset_path_css(self):
        """Should return CSS asset path."""
        html = self._render('{% load rspack %}{% rspack_asset_path "application.css" %}')
        assert html == "/packs/application-def456.css"

    def test_rspack_asset_url_with_host(self, settings, tmp_project, sample_manifest_data):
        """Should prepend asset_host to the path."""
        reset_config()
        reset_manifest()
        settings.RSPACK = {"asset_host": "https://cdn.example.com"}
        (tmp_project / "public" / "packs" / "manifest.json").write_text(
            json.dumps(sample_manifest_data)
        )
        html = self._render('{% load rspack %}{% rspack_asset_url "application.js" %}')
        assert html == "https://cdn.example.com/packs/application-abc123.js"

    def test_js_deduplication(self):
        """Should not output the same script path twice."""
        html = self._render('{% load rspack %}{% rspack_bundle_js "application" %}')
        # Each path should appear only once
        assert html.count("/packs/application-abc123.js") == 1

    def test_missing_pack_raises(self):
        """Should raise on missing packs."""
        from django_rspack.manifest import MissingEntryError

        with pytest.raises(MissingEntryError):
            self._render('{% load rspack %}{% rspack_bundle_js "nonexistent" %}')
