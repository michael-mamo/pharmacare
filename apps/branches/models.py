"""
Branches (multi-location support).

Design decisions worth understanding before changing anything here
------------------------------------------------------------------

**What is shared and what is per-branch.** The product catalogue
(medicines, categories, suppliers) and customers are deliberately
*shared* across every branch: a paracetamol is the same product in Bole
as in Gondar, and a customer should keep one loyalty balance wherever
they shop. What differs per branch is **stock**, and everything that
moves stock — sales, purchases, batches and stock movements.

**Why a separate BranchStock row instead of a branch field on Medicine.**
Stock is a property of the *pair* (branch, product), not of the product.
Putting it on Medicine would force one row per product per branch and
duplicate every name, price and barcode — which then drift apart.
`BranchStock` holds quantity and reorder level; `Medicine.quantity`
survives as a **cached total across all branches**, kept in step by
`BranchStock.save()`, so existing group-level reports and the
Administrator dashboard keep working unchanged.

**Reorder level is per branch on purpose.** A busy city branch and a
small rural one should not be forced to reorder at the same threshold.
`BranchStock.reorder_level` seeds itself from the product's default the
first time stock appears at a branch, then diverges freely.

**One main branch.** `is_main` marks the default landing branch for
Administrators and the fallback when something has no branch recorded
(legacy rows from before this feature). Exactly one branch is main;
`save()` enforces that rather than trusting callers.
"""
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel

phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-()]{7,20}$",
    message=_("Enter a valid phone number."),
)


class Branch(OrganizationOwnedModel):
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Branch Name"))
    code = models.CharField(
        max_length=12, unique=True, editable=False, verbose_name=_("Branch Code"),
        help_text=_("Auto-generated, e.g. BR-001. Appears on invoices and reports."),
    )
    phone = models.CharField(
        max_length=20, blank=True, validators=[phone_validator], verbose_name=_("Phone")
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    city = models.CharField(max_length=80, blank=True, verbose_name=_("City / Town"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    license_number = models.CharField(
        max_length=80, blank=True, verbose_name=_("Licence Number"),
        help_text=_("This branch's own operating licence, printed on its invoices."),
    )
    manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_branches", verbose_name=_("Branch Manager"),
    )
    invoice_prefix = models.CharField(
        max_length=10, blank=True, verbose_name=_("Invoice Prefix"),
        help_text=_("Optional. Overrides the pharmacy-wide prefix so each branch's "
                    "invoice numbers are distinguishable, e.g. BOL-."),
    )
    is_main = models.BooleanField(
        default=False, verbose_name=_("Main Branch"),
        help_text=_("The default branch. Exactly one branch is the main one."),
    )
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name=_("Active"),
        help_text=_("Inactive branches keep their history but cannot record new "
                    "sales, purchases or stock movements."),
    )
    opened_on = models.DateField(null=True, blank=True, verbose_name=_("Opened On"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")
        ordering = ["-is_main", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("branches:branch_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        # The very first branch created is automatically the main one, so a
        # fresh install is never left without a default.
        if is_new and not Branch.objects.exists():
            self.is_main = True
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"BR-{self.pk:03d}"
            super().save(update_fields=["code"])
        # Enforce a single main branch here rather than relying on callers.
        if self.is_main:
            Branch.objects.exclude(pk=self.pk).filter(is_main=True).update(is_main=False)

    def delete(self, *args, **kwargs):
        """Blocked once the branch has trading history. Deleting it would
        orphan sales and stock records that must remain auditable."""
        if self.sales.exists() or self.purchase_invoices.exists():
            raise models.ProtectedError(
                str(_("This branch has sales or purchases recorded and cannot be "
                      "deleted. Mark it inactive instead.")),
                {self},
            )
        super().delete(*args, **kwargs)

    # ---- stock summaries ------------------------------------------------
    @property
    def total_stock_units(self):
        return self.stock_levels.aggregate(t=models.Sum("quantity"))["t"] or 0

    @property
    def product_count(self):
        return self.stock_levels.filter(quantity__gt=0).count()

    @property
    def low_stock_count(self):
        return self.stock_levels.filter(
            quantity__gt=0, quantity__lte=models.F("reorder_level")
        ).count()

    @property
    def out_of_stock_count(self):
        return self.stock_levels.filter(quantity=0).count()

    @property
    def staff_count(self):
        return self.staff.filter(is_active=True).count()


class BranchStock(models.Model):
    """Stock level of one product at one branch.

    This is the authoritative quantity for anything branch-scoped: the till
    validates against it, low-stock alerts read it, and transfers move it.
    """

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="stock_levels",
        verbose_name=_("Branch"),
    )
    medicine = models.ForeignKey(
        "medicine.Medicine", on_delete=models.CASCADE, related_name="branch_stocks",
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(
        default=0, db_index=True, verbose_name=_("Quantity in Stock")
    )
    reorder_level = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(0)], verbose_name=_("Reorder Level"),
        help_text=_("Per branch, so a busy branch can reorder earlier than a quiet one."),
    )
    shelf_location = models.CharField(
        max_length=60, blank=True, verbose_name=_("Shelf / Location"),
        help_text=_("Where this sits in this particular branch, e.g. 'Aisle 3, Shelf B'."),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Branch Stock Level")
        verbose_name_plural = _("Branch Stock Levels")
        ordering = ["branch__name", "medicine__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "medicine"], name="unique_stock_per_branch_product"
            )
        ]
        indexes = [
            models.Index(fields=["branch", "quantity"]),
            models.Index(fields=["medicine"]),
        ]

    def __str__(self):
        return f"{self.medicine.name} @ {self.branch.name}: {self.quantity}"

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.reorder_level

    @property
    def is_out_of_stock(self):
        return self.quantity == 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_medicine_total(self.medicine_id)

    @staticmethod
    def sync_medicine_total(medicine_id):
        """Refreshes `Medicine.quantity` to the sum across all branches.

        Kept as a cached rollup so pharmacy-wide reports, the Administrator
        dashboard and the shared catalogue list can show a group total
        without a join, and so code predating branches still reads a
        sensible number.
        """
        from apps.medicine.models import Medicine

        total = (
            BranchStock.objects.filter(medicine_id=medicine_id)
            .aggregate(t=models.Sum("quantity"))["t"]
            or 0
        )
        Medicine.objects.filter(pk=medicine_id).update(quantity=total)

    @classmethod
    @transaction.atomic
    def get_or_create_for(cls, branch, medicine):
        """Row for this pair, seeding the reorder level from the product's
        own default the first time the product reaches this branch."""
        obj, created = cls.objects.get_or_create(
            branch=branch,
            medicine=medicine,
            defaults={"quantity": 0, "reorder_level": medicine.reorder_level or 10},
        )
        return obj
