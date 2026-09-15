"""
Inspect or generate fiscal years.

    python manage.py fiscal_years                # show the rule and periods
    python manage.py fiscal_years --generate 5   # create the next 5

Changing the rule (in Settings or the admin) affects only years generated
afterwards. Periods already created keep their dates, so transactions never
move between years.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.ethiopian_calendar import format_ethiopian
from apps.core.fiscal import FiscalYear, FiscalYearSettings
from apps.core.services import generate_fiscal_years


class Command(BaseCommand):
    help = "Show or generate fiscal years."

    def add_arguments(self, parser):
        parser.add_argument("--generate", type=int, default=0,
                            help="Generate this many fiscal years from today.")

    def handle(self, *args, **options):
        settings = FiscalYearSettings.load()
        self.stdout.write(self.style.MIGRATE_HEADING("Fiscal year rule"))
        self.stdout.write(f"  Calendar : {settings.get_calendar_system_display()}")
        self.stdout.write(f"  Starts   : {settings.start_label}")
        self.stdout.write(f"  Displayed: {settings.get_display_calendar_display()}")

        today = timezone.localdate()
        start, end, label = settings.period_for(today)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Current period (from the rule)"))
        self.stdout.write(f"  {label}: {start} → {end}")
        self.stdout.write(f"  Ethiopian: {format_ethiopian(start)} → {format_ethiopian(end)}")

        count = options["generate"]
        if count:
            created = generate_fiscal_years(count=count)
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"Generated {len(created)} year(s)."))

        stored = FiscalYear.objects.order_by("start_date")
        if stored:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Stored fiscal years"))
            for year in stored:
                marker = " (current)" if year.is_current else ""
                self.stdout.write(
                    f"  {year.label:12s} {year.start_date} → {year.end_date}  "
                    f"{year.get_status_display()}{marker}"
                )
        else:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "No fiscal years stored yet. Run with --generate 3."
            ))
