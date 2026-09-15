from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    label = "dashboard"
    verbose_name = "Dashboard"

    def ready(self):
        # Registers the template sanity checks so they run on manage.py check.
        from . import checks  # noqa: F401
