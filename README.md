# django-rspack

Django integration for [Rspack](https://rspack.dev/), a Rust-powered bundler compatible with webpack.

`django-rspack` is the Django equivalent of [Shakapacker](https://github.com/shakacode/shakapacker) for Rails. It reuses the same JavaScript/npm package from Shakapacker for the actual Rspack dev server, config, manifest handling, and build pipeline. The Python side is a thin Django app that integrates Rspack into your Django project.

## Features

- **Manifest-based asset resolution** — Reads the Rspack manifest.json to resolve pack names to fingerprinted paths
- **Django template tags** — `{% rspack_bundle_js %}`, `{% rspack_bundle_css %}` to inject script/link tags
- **Management commands** — `rspack_install`, `rspack_dev_server`, `rspack_compile`
- **Dev server proxy middleware** — Proxies asset requests to the Rspack dev server in development
- **Django staticfiles integration** — Works with `collectstatic` for production asset serving
- **Content hashing** — Fingerprinted filenames for production cache busting
- **Code splitting support** — Handles webpack/rspack entrypoints with multiple chunks

## Requirements

- Python 3.10+
- Django 4.2+
- Node.js 18+ (for Rspack)

## Quick Start

### 1. Install the Python package

```bash
pip install django-rspack
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_rspack",
]
```

### 3. Run the installer

```bash
python manage.py rspack_install
```

This creates:
- `config/shakapacker.yml` — Configuration file
- `rspack.config.js` — Rspack configuration
- `app/javascript/packs/application.js` — Default entry point
- `package.json` — Node.js package file (if it doesn't exist)

### 4. Install npm packages

```bash
npm install
```

### 5. Use in templates

```html
{% load rspack %}
<!DOCTYPE html>
<html>
<head>
    {% rspack_bundle_css "application" %}
</head>
<body>
    {% rspack_bundle_js "application" %}
</body>
</html>
```

### 6. Start the dev server

```bash
python manage.py rspack_dev_server
```

## Configuration

Configuration is loaded from three sources (in order of precedence):

1. **Django settings** (`RSPACK` dict in settings.py)
2. **YAML config file** (`config/shakapacker.yml`)
3. **Bundled defaults**

### Django Settings

```python
# settings.py
RSPACK = {
    "source_path": "app/javascript",
    "source_entry_path": "packs",
    "public_root_path": "public",
    "public_output_path": "packs",
    "dev_server": {
        "host": "localhost",
        "port": 3035,
    },
}
```

### Environment Variables

| Variable | Description |
|---|---|
| `RSPACK_ENV` | Override environment detection (`development`, `production`, `test`) |
| `RSPACK_DEV_SERVER_HOST` | Override dev server host |
| `RSPACK_DEV_SERVER_PORT` | Override dev server port |
| `RSPACK_ASSET_HOST` | CDN or asset host URL |

See [Configuration Guide](docs/configuration.md) for all options.

## Template Tags

```html
{% load rspack %}

{# JavaScript bundle with defer (default) #}
{% rspack_bundle_js "application" %}

{# CSS bundle #}
{% rspack_bundle_css "application" %}

{# Generic bundle (specify type) #}
{% rspack_bundle "application" "js" %}

{# Get just the asset path #}
{% rspack_asset_path "application.js" %}

{# Get the full URL (with asset host) #}
{% rspack_asset_url "application.js" %}
```

## Management Commands

```bash
# Install configuration and scaffolding
python manage.py rspack_install

# Start the development server
python manage.py rspack_dev_server

# Compile assets for production
python manage.py rspack_compile
```

## Dev Server Middleware

Add the middleware to proxy asset requests to the Rspack dev server during development:

```python
# settings.py
MIDDLEWARE = [
    "django_rspack.middleware.RspackDevServerMiddleware",
    ...
]
```

The middleware only activates in development mode when the dev server is running.

## Production Deployment

1. Compile assets:
   ```bash
   python manage.py rspack_compile
   ```

2. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

3. Configure your web server to serve the `public/packs/` directory.

See [Deployment Guide](docs/deployment.md) for detailed instructions.

## Development

```bash
# Clone the repository
git clone https://github.com/shakacode/django-rspack.git
cd django-rspack

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## Related Projects

- [Shakapacker](https://github.com/shakacode/shakapacker) — The Rails equivalent (Ruby gem + npm package)
- [Rspack](https://rspack.dev/) — The Rust-powered bundler
- [React on Rails](https://github.com/shakacode/react_on_rails) — React integration for Rails

## License

MIT License. See [LICENSE](LICENSE) for details.

## About

Created and maintained by [ShakaCode](https://www.shakacode.com/).
