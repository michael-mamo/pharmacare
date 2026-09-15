"""
Wipes every pharmacy (organization) and everything it owns, for a clean
restart. Keeps two things deliberately untouched:

  - Platform staff (System Administrator) accounts
  - The shared standard catalogue (CatalogueProduct / CatalogueCategory —
    platform-level reference data, not any pharmacy's own)

Everything else goes: every organization, branch, medicine, category,
customer, supplier, sale, purchase, stock movement, payment, and every
non-platform-staff user account.

    python manage.py reset_pharmacies --dry-run   # see what would be deleted
    python manage.py reset_pharmacies --yes        # actually do it

Deletion runs in dependency order so PROTECT constraints (a Branch with
sales history, a Medicine with purchase history, etc.) never block it —
the children go first, in a single transaction, so a failure partway
through leaves nothing half-deleted.

After running this, the correct way back to a working system is: create a
pharmacy from Pharmacies → Add Pharmacy, switch into it, then add its
first Administrator from Staff & Roles — the same flow this command exists
to make sure everyone actually goes through, rather than data left over
from before organizations existed.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Role, User
from apps.branches.models import Branch, BranchStock
from apps.customers.models import Customer
from apps.inventory.models import StockMovement
from apps.inventory.stocktake import StockTake
from apps.medicine.models import Category, Medicine
from apps.organizations.models import Organization, Payment, unscoped
from apps.purchases.models import PurchaseInvoice, PurchaseItem
from apps.sales.models import Sale, SaleItem
from apps.suppliers.models import Supplier


class Command(BaseCommand):
    help = "Delete every pharmacy and its data. Keeps platform staff and the shared catalogue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true",
            help="Actually perform the deletion. Without this, only reports counts.",
        )

    def handle(self, *args, **options):
        confirmed = options["yes"]

        with unscoped():
            counts = {
                "Organizations": Organization.objects.count(),
                "Branches": Branch.objects.count(),
                "Medicines": Medicine.objects.count(),
                "Categories": Category.objects.count(),
                "Customers": Customer.objects.count(),
                "Suppliers": Supplier.objects.count(),
                "Sales": Sale.objects.count(),
                "Purchase invoices": PurchaseInvoice.objects.count(),
                "Stock movements": StockMovement.objects.count(),
                "Stocktakes": StockTake.objects.count(),
                "Payments": Payment.objects.count(),
                "Non-platform users": User.objects.exclude(role=Role.SYSTEM_ADMIN).count(),
            }

        self.stdout.write("This would delete:")
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write(self.style.SUCCESS(
            "\nKept untouched: Platform staff (System Administrator) accounts, "
            "and the shared standard catalogue."
        ))

        if not confirmed:
            self.stdout.write(self.style.WARNING(
                "\nDry run only — nothing was deleted. Re-run with --yes to actually do this."
            ))
            return

        if sum(counts.values()) == 0:
            self.stdout.write("Nothing to delete.")
            return

        with transaction.atomic(), unscoped():
            # Children before parents, so PROTECT constraints never block
            # this — Sale/PurchaseInvoice/StockTake cascade-delete their
            # own line items, which is what clears the PROTECT each held
            # against Medicine (and StockTake's own PROTECT against Branch).
            Sale.objects.all().delete()
            PurchaseInvoice.objects.all().delete()
            StockMovement.objects.all().delete()
            StockTake.objects.all().delete()
            BranchStock.objects.all().delete()
            Medicine.objects.all().delete()
            Category.objects.all().delete()
            Customer.objects.all().delete()
            Supplier.objects.all().delete()
            Branch.objects.all().delete()
            User.objects.exclude(role=Role.SYSTEM_ADMIN).delete()
            # Payment cascades automatically as part of Organization, but
            # deleting it explicitly first keeps the collector small.
            Payment.objects.all().delete()
            Organization.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            "\nDone. Every pharmacy and its data is gone. Platform staff and the "
            "standard catalogue are untouched.\n"
            "Next: log in as platform staff → Pharmacies → Add Pharmacy, switch "
            "into it, then add its first Administrator from Staff & Roles."
        ))
