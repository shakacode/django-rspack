# Configuration

django-rspack loads configuration from three sources, in order of precedence:

1. **Django settings** — `RSPACK` dict in `settings.py`
2. **YAML config file** — `config/shakapacker.yml` (same format as Shakapacker for Rails)
3. **Bundled defaults** — Sensible defaults shipped with the package

## Django settings

```python
# settings.py
RSPACK = {
    "source_path": "app/javascript",
    "source_entry_path": "packs",
    "public_root_path": "public",
    "public_output_path": "packs",
    "cache_manifest": False,
    "compile": True,
    "dev_server": {
        "host": "localhost",
        "port": 3035,
        "server": "http",
        "hmr": False,
    },
}
```

## YAML config file

The YAML file uses environment-specific sections:

```yaml
# config/shakapacker.yml
default: &default
  source_path: app/javascript
  source_entry_path: packs
  public_root_path: public
  public_output_path: packs

development:
  <<: *default
  compile: true
  dev_server:
    host: localhost
    port: 3035

production:
  <<: *default
  compile: false
  cache_manifest: true
```

## All configuration options

### Paths

| Option | Default | Description |
|---|---|---|
| `source_path` | `app/javascript` | Root directory for JavaScript/CSS source files |
| `source_entry_path` | `packs` | Subdirectory containing entry points (relative to source_path) |
| `public_root_path` | `public` | Public root directory |
| `public_output_path` | `packs` | Output directory for compiled assets (relative to public_root_path) |
| `manifest_path` | `<public_output_path>/manifest.json` | Path to the manifest file |
| `cache_path` | `tmp/rspack` | Directory for build cache |
| `config_path` | `config/shakapacker.yml` | Path to the YAML config file |

### Compilation

| Option | Default (dev) | Default (prod) | Description |
|---|---|---|---|
| `compile` | `true` | `false` | Enable auto-compilation when assets are requested |
| `compile_output` | `true` | `true` | Show Rspack compilation output |
| `cache_manifest` | `false` | `true` | Cache manifest.json in memory |
| `compiler_strategy` | `mtime` | `digest` | How to check if assets are stale (`mtime` or `digest`) |
| `useContentHash` | `false` | `true` | Use content hashes in output filenames |
| `nested_entries` | `true` | `true` | Allow entry points in subdirectories |

### Dev server

| Option | Default | Description |
|---|---|---|
| `dev_server.host` | `localhost` | Dev server hostname |
| `dev_server.port` | `3035` | Dev server port |
| `dev_server.server` | `http` | Protocol (`http` or `https`) |
| `dev_server.hmr` | `false` | Enable Hot Module Replacement |
| `dev_server.inline_css` | `true` | Inline CSS via JavaScript (for HMR) |
| `dev_server.compress` | `true` | Enable gzip compression |

### Asset delivery

| Option | Default | Description |
|---|---|---|
| `asset_host` | `None` | CDN or asset host URL |
| `integrity.enabled` | `false` | Enable Subresource Integrity (SRI) |
| `integrity.hash_functions` | `["sha384"]` | SRI hash algorithms |
| `integrity.cross_origin` | `anonymous` | CORS setting for SRI |

## Environment variables

| Variable | Description |
|---|---|
| `RSPACK_ENV` | Override environment detection (`development`, `production`, `test`) |
| `RSPACK_DEV_SERVER_HOST` | Override dev server host |
| `RSPACK_DEV_SERVER_PORT` | Override dev server port |
| `RSPACK_DEV_SERVER_SERVER` | Override dev server protocol |
| `RSPACK_ASSET_HOST` | Override asset host URL |

## Environment detection

By default, django-rspack maps Django's `DEBUG` setting:

- `DEBUG = True` → `development` environment
- `DEBUG = False` → `production` environment

Override with the `RSPACK_ENV` environment variable:

```bash
RSPACK_ENV=production python manage.py rspack_compile
```

## Accessing configuration in code

```python
from django_rspack.conf import get_config

config = get_config()
print(config.manifest_path)
print(config.dev_server_url)
print(config.compile)
```
