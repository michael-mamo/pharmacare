"""
Creates a platform (system) administrator.

    python manage.py create_system_admin --username you --email you@example.com

Platform staff belong to **no organization**. That null is what grants
platform scope, so this command deliberately does not accept one — assigning
an organization would demote the account to an ordinary pharmacy user.

By design, a system administrator sees no pharmacy business data until they
explicitly select an organization to work inside. That keeps the boundary
visible rather than implicit.
"""
import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role, User


class Command(BaseCommand):
    help = "Create a platform (system) administrator account."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument(
            "--password", default=None,
            help="Omit to be prompted. Passing it on the command line leaves it "
                 "in your shell history.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError(f"A user named '{username}' already exists.")

        password = options["password"]
        if not password:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                raise CommandError("Passwords did not match.")

        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError("Password rejected: " + "; ".join(e.messages))

        user = User.objects.create_user(
            username=username, password=password, email=options["email"],
            first_name=options["first_name"], last_name=options["last_name"],
            role=Role.SYSTEM_ADMIN, is_staff=True, is_superuser=True,
            force_password_change=False,
        )
        # Belt and braces: the save() hook already exempts system admins, but
        # an organization here would silently break platform scope.
        if user.organization_id is not None:
            user.organization = None
            user.save(update_fields=["organization"])

        self.stdout.write(self.style.SUCCESS(
            f"System administrator '{username}' created with no organization."
        ))
        self.stdout.write(
            "They will see no pharmacy data until they select an organization "
            "to work inside."
        )
