"""
Rebuilds condition-based notifications (low stock, expiry, pending payment).

Schedule this rather than relying on page-load refreshes if you want alerts
to be current even when nobody is logged in. On Windows use Task Scheduler:

    python manage.py refresh_notifications
"""
from django.core.management.base import BaseCommand

from apps.notifications.services import refresh_notifications


class Command(BaseCommand):
    help = "Rescan stock, expiry and payment state and update notifications."

    def handle(self, *args, **options):
        result = refresh_notifications()
        self.stdout.write(self.style.SUCCESS(
            f"Active alerts: {result['active']}, resolved: {result['resolved']}"
        ))
