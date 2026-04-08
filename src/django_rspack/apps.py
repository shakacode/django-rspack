from django.apps import AppConfig


class RspackConfig(AppConfig):
    name = "django_rspack"
    verbose_name = "Django Rspack"

    def ready(self) -> None:
        # Import conf to trigger configuration loading on app startup
        from django_rspack import conf  # noqa: F401
