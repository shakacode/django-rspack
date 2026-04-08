# Getting Started with django-rspack

This guide walks you through setting up django-rspack in a new or existing Django project.

## Prerequisites

- Python 3.10+
- Django 4.2+
- Node.js 18+ and npm

## Installation

### 1. Install the Python package

```bash
pip install django-rspack
```

### 2. Add to your Django settings

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

This creates the following files:

| File | Purpose |
|---|---|
| `config/shakapacker.yml` | Main configuration file |
| `rspack.config.js` | Rspack bundler configuration |
| `app/javascript/packs/application.js` | Default JavaScript entry point |
| `package.json` | Node.js package file (if not present) |

### 4. Install Node.js packages

```bash
npm install
```

This installs the `shakapacker` npm package and Rspack CLI tools.

### 5. Add template tags to your templates

```html
{% load rspack %}
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>
    {% rspack_bundle_css "application" %}
</head>
<body>
    <h1>Hello, django-rspack!</h1>
    {% rspack_bundle_js "application" %}
</body>
</html>
```

### 6. Start the dev server

In a separate terminal:

```bash
python manage.py rspack_dev_server
```

Then start Django:

```bash
python manage.py runserver
```

## Optional: Dev server proxy middleware

To automatically proxy asset requests to the Rspack dev server during development, add the middleware:

```python
# settings.py
MIDDLEWARE = [
    "django_rspack.middleware.RspackDevServerMiddleware",
    ...
]
```

This is optional — without it, the dev server serves assets directly on its own port (default: 3035).

## Adding CSS

Create a CSS file and import it from your entry point:

```css
/* app/javascript/packs/application.css */
body {
  font-family: system-ui, sans-serif;
}
```

```javascript
// app/javascript/packs/application.js
import "./application.css";
console.log("Hello from django-rspack!");
```

Then add the CSS tag to your template:

```html
{% rspack_bundle_css "application" %}
```

## Multiple entry points

Create additional entry files in `app/javascript/packs/`:

```javascript
// app/javascript/packs/admin.js
console.log("Admin panel JS");
```

Update your `rspack.config.js`:

```javascript
entry: {
  application: path.resolve(__dirname, "app/javascript/packs/application.js"),
  admin: path.resolve(__dirname, "app/javascript/packs/admin.js"),
},
```

Use them in different templates:

```html
{% rspack_bundle_js "admin" %}
```

## Next steps

- [Configuration Guide](configuration.md) — All available settings
- [Deployment Guide](deployment.md) — Production deployment instructions
