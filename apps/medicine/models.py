"""
Medicine catalog models: Category and Medicine.

Design notes
------------
- `Medicine.code` is auto-generated (MED-000001, ...) on first save so staff
  never have to invent a unique code — the display order is stable and
  human-scannable, which matters when printing shelf labels.
- Money fields use DecimalField, never float, to avoid rounding errors in
  a financial context.
- `quantity` and `reorder_level` are plain integers; the low-stock and
  expiry KPIs on the Phase 1 dashboard already query these field names
  directly (see apps/dashboard/views.py), so they must not be renamed
  without updating that file too.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel


class Category(OrganizationOwnedModel):
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Category Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("medicine:category_list")

    @property
    def medicine_count(self):
        return self.medicines.count()


barcode_validator = RegexValidator(
    regex=r"^[0-9A-Za-z\-]{6,32}$",
    message="Barcode must be 6-32 characters (letters, numbers, hyphens only).",
)


class ProductType(models.TextChoices):
    """What kind of thing this is.

    The catalogue was medicine-only at first, but a pharmacy counter also
    sells cosmetics, dressings and devices. Rather than a second parallel
    catalogue (which would split stock, sales and reporting in two), the
    same record now carries a type. Everything downstream — POS, batches,
    reports, expiry alerts — works unchanged for every type.
    """

    MEDICINE = "MEDICINE", _("Medicine")
    COSMETIC = "COSMETIC", _("Cosmetic / Personal Care")
    MEDICAL_SUPPLY = "SUPPLY", _("Medical Supply")          # bandages, gauze, syringes
    MEDICAL_DEVICE = "DEVICE", _("Medical Device / Support")  # knee braces, BP monitors
    SUPPLEMENT = "SUPPLEMENT", _("Supplement / Vitamin")
    BABY_CARE = "BABY", _("Baby & Mother Care")
    OTHER = "OTHER", _("Other")

    @classmethod
    def non_expiring_types(cls):
        """Types where an expiry date usually doesn't apply. A knee brace or
        a BP monitor has no shelf life; a bandage or cosmetic often does, so
        those stay expiry-capable and simply allow it to be blank."""
        return {cls.MEDICAL_DEVICE, cls.OTHER}


class Unit(models.TextChoices):
    TABLET = "TABLET", "Tablet"
    CAPSULE = "CAPSULE", "Capsule"
    BOTTLE = "BOTTLE", "Bottle"
    VIAL = "VIAL", "Vial"
    TUBE = "TUBE", "Tube"
    BOX = "BOX", "Box"
    STRIP = "STRIP", "Strip"
    ML = "ML", "Milliliter"
    MG = "MG", "Milligram"
    PIECE = "PIECE", "Piece"
    PACK = "PACK", "Pack"
    ROLL = "ROLL", "Roll"          # bandages, tape
    PAIR = "PAIR", "Pair"          # supports, gloves
    SACHET = "SACHET", "Sachet"
    JAR = "JAR", "Jar"             # creams, cosmetics
    UNIT = "UNIT", "Unit"


class Medicine(OrganizationOwnedModel):
    code = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name=_("Medicine Code"),
        help_text=_("Auto-generated on save (e.g. MED-000001)."),
    )
    barcode = models.CharField(
        max_length=32, blank=True, null=True, unique=True,
        validators=[barcode_validator], verbose_name=_("Barcode"),
    )
    catalogue_product = models.ForeignKey(
        "catalogue.CatalogueProduct", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medicines", verbose_name=_("Catalogue Product"),
        help_text=_("The standard catalogue record this stock item is registered "
                    "against. Linking keeps naming consistent and makes group "
                    "reporting possible. Leave blank only for something genuinely "
                    "not in the catalogue."),
    )
    product_type = models.CharField(
        max_length=12, choices=ProductType.choices, default=ProductType.MEDICINE,
        db_index=True, verbose_name=_("Product Type"),
        help_text=_("Medicines, cosmetics, dressings, devices and supplements all "
                    "live in this one catalogue."),
    )
    name = models.CharField(max_length=200, verbose_name=_("Product Name"), db_index=True)
    generic_name = models.CharField(max_length=200, blank=True, verbose_name=_("Generic Name"))
    brand = models.CharField(max_length=150, blank=True, verbose_name=_("Brand"))
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="medicines", verbose_name=_("Category")
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medicines", verbose_name=_("Supplier"),
    )
    batch_number = models.CharField(max_length=60, blank=True, verbose_name=_("Batch Number"))
    manufacturing_date = models.DateField(null=True, blank=True, verbose_name=_("Manufacturing Date"))
    expiry_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Expiry Date"),
        help_text=_("Leave blank for items that do not expire, such as a knee "
                    "support or a blood-pressure monitor."),
    )

    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Purchase Price"),
        help_text=_("Cost price — visible to Administrators and Store Managers only."),
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Selling Price"),
    )
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Tax (%)"),
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Discount (%)"),
    )

    quantity = models.PositiveIntegerField(default=0, verbose_name=_("Quantity in Stock"))
    reorder_level = models.PositiveIntegerField(
        default=10, verbose_name=_("Reorder Level"),
        help_text=_("Triggers a Low Stock warning when quantity falls to or below this level."),
    )
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.TABLET, verbose_name=_("Unit"))

    description = models.TextField(blank=True, verbose_name=_("Description"))
    image = models.ImageField(upload_to="medicines/%Y/%m/", blank=True, null=True, verbose_name=_("Photo"))

    requires_prescription = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Requires Prescription"),
        help_text=_("Shows a clear warning at the till before this item is sold."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["quantity"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["product_type"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=0), name="medicine_selling_price_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_absolute_url(self):
        return reverse("medicine:medicine_detail", kwargs={"pk": self.pk})

    def full_clean(self, *args, **kwargs):
        """Locks name/generic_name/brand to the linked catalogue record
        *before* field-level validation runs, so a blank `name` on a
        catalogue-linked medicine is filled in time to pass the "required"
        check in clean_fields() — clean() below runs too late for that,
        since Django validates individual fields first and only calls
        clean() afterwards. Applies on every entry path (this form, the
        "Register from Catalogue" screen, Django admin, future imports),
        because a pharmacy can price a catalogue product however it likes
        but cannot rename it — the whole point of linking is that the same
        molecule always reads the same across every pharmacy."""
        if self.catalogue_product_id:
            cp = self.catalogue_product
            self.generic_name = cp.generic_name
            self.brand = cp.brand_name
            if not self.name:
                self.name = cp.short_name
        return super().full_clean(*args, **kwargs)

    def clean(self):
        """Expiry is required for anything consumable or applied to the body,
        and optional for durable goods. Enforced here rather than at the DB
        level so the message can explain itself."""
        from django.core.exceptions import ValidationError

        super().clean()
        if not self.expiry_date and self.product_type not in ProductType.non_expiring_types():
            raise ValidationError({
                "expiry_date": _(
                    "An expiry date is required for this product type. Leave it "
                    "blank only for items that genuinely do not expire, and set "
                    "the product type to Medical Device or Other."
                )
            })

        # Linking a Medicine to the catalogue is strongly recommended, not
        # required: the shared catalogue is a ~600-item essential-medicines
        # list (see docs/CATALOGUE_IMPORT.md), and a real pharmacy legitimately
        # stocks plenty of genuine medicines that simply aren't on it. Blocking
        # those outright would just push pharmacies toward miscategorising
        # real stock as "Other" to get around the rule — worse than the
        # inconsistency it was meant to prevent. So an unlinked Medicine is
        # allowed; it's flagged instead (see is_standardized / the "Not
        # Standardised" badge in the medicine list and detail templates,
        # and the warning message shown on save in MedicineCreateView) so
        # it stays visible and easy to reconcile against the catalogue
        # later, rather than silently blending in.
        if self.catalogue_product_id:
            already = Medicine.objects.filter(
                catalogue_product_id=self.catalogue_product_id
            ).exclude(pk=self.pk).first()
            if already:
                raise ValidationError({
                    "catalogue_product": _(
                        '"%(name)s" is already registered as %(code)s. Edit that '
                        "product instead of registering it a second time."
                    ) % {"name": self.catalogue_product.display_name, "code": already.code}
                })

    @property
    def is_standardized(self):
        """True unless this is a Medicine that was added without a
        catalogue link — the "Not Standardised" case worth flagging in
        the UI and in reporting."""
        return self.product_type != ProductType.MEDICINE or self.catalogue_product_id is not None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.code:
            self.code = f"MED-{self.pk:06d}"
            super().save(update_fields=["code"])
        if is_new:
            self._seed_branch_stock()

    def _seed_branch_stock(self):
        """Puts any opening quantity into a real branch stock row.

        Without this, a product created with a quantity would show stock on
        the shared catalogue page but none at any branch, so it could never
        be sold — `Medicine.quantity` is only a rollup of the per-branch
        figures, not a place stock can actually live.

        The opening quantity goes to the main branch, since a product form
        has no branch field; move it afterwards with a Stock Transfer.
        """
        try:
            from apps.branches.models import Branch, BranchStock
        except Exception:  # pragma: no cover - during initial migrations
            return
        branch = (
            Branch.objects.filter(is_main=True, is_active=True).first()
            or Branch.objects.filter(is_active=True).first()
        )
        if branch is None:
            return
        BranchStock.objects.update_or_create(
            branch=branch, medicine=self,
            defaults={"quantity": self.quantity or 0,
                      "reorder_level": self.reorder_level or 10},
        )
        # Record the opening balance in the stock ledger. Without this the
        # ledger has no starting point, so its first entry would show a
        # balance appearing out of nowhere and the running balance could not
        # be reconciled back to zero.
        opening = self.quantity or 0
        if opening:
            try:
                from apps.inventory.allocation import _write_ledger
                from apps.inventory.stocktake import LedgerSource

                _write_ledger(
                    branch=branch, medicine=self, delta=opening,
                    before=0, after=opening, source=LedgerSource.OPENING,
                    unit_cost=self.purchase_price or None,
                    note="Opening quantity entered when the product was created",
                )
            except Exception:  # pragma: no cover - never block product creation
                pass

    def stock_at(self, branch):
        """Units on hand at one branch."""
        if branch is None:
            return self.quantity or 0
        from apps.branches.models import BranchStock

        row = BranchStock.objects.filter(branch=branch, medicine=self).first()
        return row.quantity if row else 0

    def reorder_level_at(self, branch):
        if branch is None:
            return self.reorder_level
        from apps.branches.models import BranchStock

        row = BranchStock.objects.filter(branch=branch, medicine=self).first()
        return row.reorder_level if row else self.reorder_level

    def is_low_stock_at(self, branch):
        qty = self.stock_at(branch)
        return 0 < qty <= self.reorder_level_at(branch)

    # ---- Derived / status helpers -----------------------------------------
    @property
    def is_low_stock(self):
        """Pharmacy-wide low-stock check, using the rolled-up total. For a
        per-branch answer use `is_low_stock_at(branch)`."""
        return self.quantity <= self.reorder_level

    @property
    def has_expiry(self):
        return self.expiry_date is not None

    @property
    def is_expired(self):
        # Items with no expiry date (devices, supports) never expire.
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.localdate()

    @property
    def expires_within_30_days(self):
        if not self.expiry_date or self.is_expired:
            return False
        return (self.expiry_date - timezone.localdate()).days <= 30

    @property
    def expires_within_60_days(self):
        if not self.expiry_date or self.is_expired:
            return False
        return (self.expiry_date - timezone.localdate()).days <= 60

    @property
    def final_price(self):
        """Selling price after discount and tax — what the customer pays."""
        discounted = self.selling_price * (Decimal("1") - self.discount_percent / Decimal("100"))
        return (discounted * (Decimal("1") + self.tax_percent / Decimal("100"))).quantize(Decimal("0.01"))
