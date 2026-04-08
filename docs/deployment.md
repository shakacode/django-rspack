# Deployment

This guide covers deploying a Django application with django-rspack to production.

## Build process

### 1. Compile assets

```bash
# Install Node.js dependencies
npm install --production

# Build assets for production
python manage.py rspack_compile
```

This runs Rspack in production mode, generating:
- Minified JavaScript bundles with content hashes
- Minified CSS bundles with content hashes
- A `manifest.json` mapping source names to fingerprinted output paths

### 2. Collect static files (optional)

If you use Django's `collectstatic` to gather all static files:

```bash
python manage.py collectstatic --noinput
```

## Production configuration

Ensure your production settings are correct:

```python
# settings.py (production)
DEBUG = False

RSPACK = {
    "cache_manifest": True,   # Cache manifest in memory for performance
    "compile": False,          # Don't auto-compile in production
}
```

Or in `config/shakapacker.yml`:

```yaml
production:
  compile: false
  cache_manifest: true
  useContentHash: true
```

## Web server configuration

### Nginx

Serve the compiled assets directly from Nginx for best performance:

```nginx
server {
    listen 80;
    server_name example.com;

    # Serve compiled Rspack assets
    location /packs/ {
        alias /path/to/your/app/public/packs/;
        expires max;
        add_header Cache-Control "public, immutable";
    }

    # Proxy other requests to Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

The `immutable` cache directive is safe because fingerprinted filenames change when content changes.

### CDN

To serve assets from a CDN:

```python
# settings.py
RSPACK = {
    "asset_host": "https://cdn.example.com",
}
```

Or via environment variable:

```bash
RSPACK_ASSET_HOST=https://cdn.example.com python manage.py runserver
```

Template tags will automatically prepend the asset host to all asset paths.

## Docker

Example Dockerfile:

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app

# Install Node.js for asset compilation
FROM base AS assets
RUN apt-get update && apt-get install -y nodejs npm
COPY package.json package-lock.json ./
RUN npm ci --production
COPY . .
RUN python manage.py rspack_compile

# Final image without Node.js
FROM base AS production
COPY --from=assets /app/public/packs /app/public/packs
COPY . .
RUN pip install -r requirements.txt
CMD ["gunicorn", "myapp.wsgi:application"]
```

## CI/CD

### GitHub Actions example

```yaml
- name: Build assets
  run: |
    npm ci --production
    python manage.py rspack_compile

- name: Collect static
  run: python manage.py collectstatic --noinput
```

## Troubleshooting

### Manifest file not found in production

If you see "Rspack manifest file not found", ensure:

1. `python manage.py rspack_compile` was run during deployment
2. The `public/packs/manifest.json` file is included in the deploy
3. `compile: false` is set for production (don't auto-compile)

### Stale assets

If you see old assets in production:

1. Clear browser cache (fingerprinted filenames should prevent this)
2. Clear CDN cache if using a CDN
3. Verify the manifest.json has the correct paths
4. Run a fresh build: `rm -rf public/packs && python manage.py rspack_compile`
