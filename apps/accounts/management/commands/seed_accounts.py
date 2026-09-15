"""
Seeds one demo staff account per role so the system can be explored
immediately after setup. Safe to re-run — uses get_or_create.

Usage:
    python manage.py seed_accounts
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User

DEMO_USERS = [
    {
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@pharmacare.local",
        "role": Role.ADMINISTRATOR,
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "pharmacist1",
        "first_name": "Selam",
        "last_name": "Bekele",
        "email": "pharmacist@pharmacare.local",
        "role": Role.PHARMACIST,
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "username": "cashier1",
        "first_name": "Dawit",
        "last_name": "Alemu",
        "email": "cashier@pharmacare.local",
        "role": Role.CASHIER,
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "username": "storemanager1",
        "first_name": "Hana",
        "last_name": "Tesfaye",
        "email": "storemanager@pharmacare.local",
        "role": Role.STORE_MANAGER,
        "is_staff": True,
        "is_superuser": False,
    },
]

DEFAULT_PASSWORD = "PharmaCare2026!"


class Command(BaseCommand):
    help = "Seed one demo staff account per role (Administrator, Pharmacist, Cashier, Store Manager)."

    def handle(self, *args, **options):
        for data in DEMO_USERS:
            username = data["username"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                    "role": data["role"],
                    "is_staff": data["is_staff"],
                    "is_superuser": data["is_superuser"],
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.force_password_change = False  # demo/eval accounts only — never do this in production
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {username} ({data['role']})"))
            else:
                self.stdout.write(self.style.WARNING(f"{username} already exists — skipped"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo accounts ready. Default password for all: {DEFAULT_PASSWORD}\n"
            "Change these immediately in any shared or production environment."
        ))
