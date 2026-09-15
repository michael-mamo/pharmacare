"""
Suspends organizations whose paid subscription period has passed.

    python manage.py expire_lapsed_subscriptions
    python manage.py expire_lapsed_subscriptions --grace-days 3
    python manage.py expire_lapsed_subscriptions --dry-run

Meant to run on a schedule (daily, via Vercel Cron or any other scheduler)
once one is set up — this is the automatic half of subscription
enforcement. `record_payment()` in apps.organizations.models is the other
half: called by a human recording a bank transfer today, or by a payment
gateway's webhook once that integration exists. Neither half needs the
other to exist first — this command works today with nothing but manually
recorded payments.

An organization with no subscription_ends_at set is never touched — blank
means "not on a metered plan" (open-ended, or a trial with no fixed end),
not "immediately overdue".
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.organizations.models import Organization, OrganizationStatus, unscoped


class Command(BaseCommand):
    help = "Suspend organizations whose subscription_ends_at has passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--grace-days", type=int, default=0,
            help="Days past subscription_ends_at before suspending. Default 0 "
                 "(suspend the day after it lapses).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would be suspended without changing anything.",
        )

    def handle(self, *args, **options):
        grace = options["grace_days"]
        dry_run = options["dry_run"]
        cutoff = date.today() - timedelta(days=grace)

        with unscoped():
            overdue = Organization.objects.filter(
                status=OrganizationStatus.ACTIVE,
                subscription_ends_at__isnull=False,
                subscription_ends_at__lt=cutoff,
            )
            names = [
                f"{org.display_name} (lapsed {org.subscription_ends_at})"
                for org in overdue
            ]
            count = len(names)
            for name in names:
                self.stdout.write(("Would suspend: " if dry_run else "Suspending: ") + name)
            if not dry_run and count:
                overdue.update(status=OrganizationStatus.SUSPENDED)

        verb = "would be suspended" if dry_run else "suspended"
        self.stdout.write(self.style.SUCCESS(f"{count} organization(s) {verb}."))
