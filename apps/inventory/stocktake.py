"""
Stock ledger and stocktake.

Two gaps this closes
--------------------

**1. The movement log was incomplete.** `StockMovement` only ever recorded
*manual* moves — stock in, out, adjustment, transfer. Sales and purchases
changed stock without writing to it, so the log could never answer "why is
this number what it is?". `StockLedger` fixes that: every single change to a
branch's stock writes one row, whatever caused it, with a running balance and
a link back to the document responsible. It is written centrally in
`allocation._adjust_branch_stock`, the one funnel all stock changes already
pass through, so a new caller cannot forget to log.

**2. Counting stock was a one-product-at-a-time chore.** A real stocktake
counts a whole branch (or a category) in one pass: you freeze a list, write
counted figures against it, review the variances, and post them together.
`StockTake` and `StockTakeLine` model that, and posting writes proper
adjustments so the ledger and batches stay in step.

The ledger is append-only. Nothing edits or deletes a row: a mistake is
corrected by another movement, exactly as with the audit log.
"""
from decimal import Decimal

from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LedgerSource(models.TextChoices):
    """What caused a stock change. Kept wider than MovementType because the
    ledger records automatic changes too, not just manual movements."""

    PURCHASE = "PURCHASE", _("Purchase received")
    SALE = "SALE", _("Sale")
    SALE_VOID = "SALE_VOID", _("Sale voided")
    PURCHASE_DELETE = "PURCHASE_DELETE", _("Purchase deleted")
    STOCK_IN = "STOCK_IN", _("Stock in")
    STOCK_OUT = "STOCK_OUT", _("Stock out")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment")
    STOCKTAKE = "STOCKTAKE", _("Stocktake")
    TRANSFER_OUT = "TRANSFER_OUT", _("Transfer out")
    TRANSFER_IN = "TRANSFER_IN", _("Transfer in")
    OPENING = "OPENING", _("Opening balance")
    RETURN = "RETURN", _("Customer return")
    OTHER = "OTHER", _("Other")


class StockLedger(models.Model):
    """One row per stock change, per branch, per product.

    `balance_after` is stored rather than computed so the ledger can be read
    back at any point in time without replaying every prior row — which is
    what makes it usable as an audit trail rather than just a list of events.
    """

    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, related_name="ledger_entries",
        verbose_name=_("Branch"),
    )
    medicine = models.ForeignKey(
        "medicine.Medicine", on_delete=models.CASCADE, related_name="ledger_entries",
        verbose_name=_("Product"),
    )
    source = models.CharField(
        max_length=20, choices=LedgerSource.choices, db_index=True,
        verbose_name=_("Cause"),
    )
    quantity_change = models.IntegerField(
        verbose_name=_("Change"),
        help_text=_("Positive for stock coming in, negative for stock going out."),
    )
    balance_before = models.PositiveIntegerField(verbose_name=_("Balance Before"))
    balance_after = models.PositiveIntegerField(verbose_name=_("Balance After"))
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_("Unit Cost"),
        help_text=_("Cost per unit of the stock that moved, where known."),
    )
    reference = models.CharField(
        max_length=60, blank=True, db_index=True, verbose_name=_("Reference"),
        help_text=_("The document behind this change, e.g. INV-000042 or PUR-000007."),
    )
    note = models.CharField(max_length=255, blank=True, verbose_name=_("Note"))
    performed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_entries", verbose_name=_("By"),
    )
    created_at = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name=_("Date")
    )

    class Meta:
        verbose_name = _("Stock Ledger Entry")
        verbose_name_plural = _("Stock Ledger")
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["branch", "medicine", "-created_at"]),
            models.Index(fields=["source"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity_change >= 0 else ""
        return f"{self.medicine_id} @ {self.branch_id}: {sign}{self.quantity_change}"

    @property
    def is_inbound(self):
        return self.quantity_change > 0

    @property
    def value_change(self):
        if self.unit_cost is None:
            return None
        return (Decimal(self.quantity_change) * self.unit_cost).quantize(Decimal("0.01"))

    @property
    def badge_class(self):
        return "bg-success-subtle text-success" if self.is_inbound else "bg-danger-subtle text-danger"


class StockTakeStatus(models.TextChoices):
    DRAFT = "DRAFT", _("In progress")
    POSTED = "POSTED", _("Posted")
    CANCELLED = "CANCELLED", _("Cancelled")


class StockTake(models.Model):
    """A physical count session for one branch.

    Opening a stocktake snapshots the *expected* quantity for every product
    in scope. That snapshot matters: counting a large branch takes hours, and
    without it a sale made mid-count would look like a counting error.
    Variance is always measured against the frozen figure.
    """

    reference = models.CharField(
        max_length=24, unique=True, editable=False, verbose_name=_("Reference")
    )
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.PROTECT, related_name="stocktakes",
        verbose_name=_("Branch"),
    )
    category = models.ForeignKey(
        "medicine.Category", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stocktakes", verbose_name=_("Category"),
        help_text=_("Limit the count to one category, for counting a section at a time. "
                    "Leave blank to count everything at this branch."),
    )
    status = models.CharField(
        max_length=10, choices=StockTakeStatus.choices, default=StockTakeStatus.DRAFT,
        db_index=True, verbose_name=_("Status"),
    )
    note = models.CharField(max_length=255, blank=True, verbose_name=_("Note"))
    started_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stocktakes_started", verbose_name=_("Started By"),
    )
    posted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stocktakes_posted", verbose_name=_("Posted By"),
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Started"))
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Posted"))

    class Meta:
        verbose_name = _("Stocktake")
        verbose_name_plural = _("Stocktakes")
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.reference} — {self.branch.name}"

    def get_absolute_url(self):
        return reverse("inventory:stocktake_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f"CNT-{self.pk:05d}"
            super().save(update_fields=["reference"])

    @property
    def is_editable(self):
        return self.status == StockTakeStatus.DRAFT

    @property
    def counted_lines(self):
        return self.lines.filter(counted_quantity__isnull=False).count()

    @property
    def total_lines(self):
        return self.lines.count()

    @property
    def progress_percent(self):
        total = self.total_lines
        if not total:
            return 0
        return int(self.counted_lines / total * 100)

    @property
    def variance_lines(self):
        """Lines where the count differs from the expected figure."""
        return [line for line in self.lines.all() if line.has_variance]

    @property
    def net_variance(self):
        return sum((line.variance or 0) for line in self.lines.all())

    @property
    def variance_value(self):
        """Money value of the discrepancy, at each product's cost. This is the
        number a manager actually cares about — 400 missing paracetamol is a
        different problem from 4 missing insulin pens."""
        total = Decimal("0.00")
        for line in self.lines.select_related("medicine"):
            if line.variance:
                cost = line.medicine.purchase_price or Decimal("0.00")
                total += Decimal(line.variance) * cost
        return total.quantize(Decimal("0.01"))


class StockTakeLine(models.Model):
    stocktake = models.ForeignKey(
        StockTake, on_delete=models.CASCADE, related_name="lines"
    )
    medicine = models.ForeignKey(
        "medicine.Medicine", on_delete=models.PROTECT, related_name="stocktake_lines",
        verbose_name=_("Product"),
    )
    expected_quantity = models.PositiveIntegerField(
        verbose_name=_("Expected"),
        help_text=_("System figure frozen when the stocktake was opened."),
    )
    counted_quantity = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Counted"),
        help_text=_("Leave blank until this product has actually been counted."),
    )
    note = models.CharField(max_length=200, blank=True, verbose_name=_("Note"))
    counted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Stocktake Line")
        verbose_name_plural = _("Stocktake Lines")
        ordering = ["medicine__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["stocktake", "medicine"], name="unique_product_per_stocktake"
            )
        ]

    def __str__(self):
        return f"{self.medicine.name}: {self.counted_quantity}/{self.expected_quantity}"

    @property
    def is_counted(self):
        return self.counted_quantity is not None

    @property
    def variance(self):
        """Counted minus expected. None until counted, so an uncounted line is
        never mistaken for a zero count — the difference matters when posting."""
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.expected_quantity

    @property
    def has_variance(self):
        return bool(self.variance)

    @property
    def variance_value(self):
        if not self.variance:
            return Decimal("0.00")
        cost = self.medicine.purchase_price or Decimal("0.00")
        return (Decimal(self.variance) * cost).quantize(Decimal("0.01"))
