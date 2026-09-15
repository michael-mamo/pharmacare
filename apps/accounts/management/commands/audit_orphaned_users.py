"""
Finds any non-platform-staff user with no organization — the exact data
state that let a System Administrator account leak into a pharmacy's own
Staff list (organization=None matching organization=None).

    python manage.py audit_orphaned_users

Read-only. Reports what it finds; fix candidates by hand (set their
organization in Django admin or the shell) or delete them if they were
never legitimate — see reset_pharmacies for a full platform-data wipe.
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User
from apps.organizations.models import unscoped


class Command(BaseCommand):
    help = "Report any non-platform-staff user with no organization set."

    def handle(self, *args, **options):
        with unscoped():
            orphans = User.objects.filter(
                organization__isnull=True
            ).exclude(role=Role.SYSTEM_ADMIN)
            count = orphans.count()
            if count == 0:
                self.stdout.write(self.style.SUCCESS(
                    "No orphaned users found — every non-platform-staff "
                    "account has an organization."
                ))
                return
            self.stdout.write(self.style.WARNING(
                f"{count} user(s) with role != SYSTEM_ADMIN and no organization:"
            ))
            for user in orphans:
                self.stdout.write(f"  {user.username} ({user.get_role_display()}) — id={user.pk}")
            self.stdout.write(
                "\nEach of these would currently show up in every pharmacy's own "
                "Staff list, and every other pharmacy's data query that assumes "
                "organization scoping. Assign each one to the correct pharmacy, "
                "or delete them if they were never legitimate."
            )
