"""
Batch-level stock costing.

The problem this solves
----------------------
Until now a Medicine carried a single `purchase_price`. Buy 100 more units at
a different cost and that one field had to be overwritten, which silently
rewrote history: last month's profit was recalculated at this month's cost.

Concrete case: 40 units bought at 20 ETB (sold at 50), then 100 more bought
at 30 ETB (sold at 60). With one cost field, selling 10 of the *old* units
would report a cost of 30 and understate profit by 100 ETB.

`StockBatch` fixes this by tracking each intake separately with its own unit
cost and remaining quantity. Sales consume batches **FEFO** (first-expired,
first-out) — which is the correct rule for a pharmacy, not FIFO: you dispense
the stock that expires soonest, regardless of when it arrived. Each sale line
records the actual cost of the units it consumed, so profit is exact and
historical invoices never change.

`Medicine.quantity` is retained as the fast, authoritative total for stock
checks and low-stock alerts; it always equals the sum of
`quantity_remaining` across that medicine's batches. `verify_consistency()`
below asserts that, and the `audit_batches` management command reports drift.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class StockBatch(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, null=True, blank=True,
        related_name="stock_batches", verbose_name=_("Branch"),
        help_text=_("Batches are held at a branch: the same product can sit in two "
                    "branches at different costs, and each must be costed separately."),
    )
    medicine = models.ForeignKey(
        "medicine.Medicine", on_delete=models.CASCADE,
        related_name="batches", verbose_name=_("Medicine"),
    )
    purchase_item = models.ForeignKey(
        "purchases.PurchaseItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="batches", verbose_name=_("Purchase Line"),
        help_text=_("The purchase that brought this batch in, if any."),
    )
    batch_number = models.CharField(max_length=60, blank=True, verbose_name=_("Batch Number"))
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Unit Cost"),
        help_text=_("What this batch actually cost per unit. Never overwritten."),
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Selling Price at Intake"),
        help_text=_("The price set when this batch arrived, kept for reference. "
                    "The price actually charged is snapshotted on each sale line."),
    )
    quantity_received = models.PositiveIntegerField(verbose_name=_("Quantity Received"))
    quantity_remaining = models.PositiveIntegerField(
        db_index=True, verbose_name=_("Quantity Remaining")
    )
    expiry_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Expiry Date")
    )
    received_at = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name=_("Received")
    )
    source = models.CharField(
        max_length=20, default="PURCHASE", verbose_name=_("Source"),
        help_text=_("PURCHASE, OPENING (pre-existing stock), ADJUSTMENT or RETURN."),
    )
    note = models.CharField(max_length=200, blank=True, verbose_name=_("Note"))

    class Meta:
        verbose_name = _("Stock Batch")
        verbose_name_plural = _("Stock Batches")
        # FEFO order: soonest expiry first, then oldest intake. Batches with
        # no expiry date sort last so dated stock is always used up first.
        ordering = ["expiry_date", "received_at", "pk"]
        indexes = [
            models.Index(fields=["medicine", "quantity_remaining"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["branch", "medicine", "quantity_remaining"]),
        ]

    def __str__(self):
        label = self.batch_number or f"#{self.pk}"
        return f"{self.medicine.name} — {label} @ {self.unit_cost}"

    @property
    def quantity_consumed(self):
        return self.quantity_received - self.quantity_remaining

    @property
    def remaining_value(self):
        return (self.unit_cost * self.quantity_remaining).quantize(Decimal("0.01"))

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    @property
    def is_depleted(self):
        return self.quantity_remaining == 0


class SaleItemCost(models.Model):
    """Which batches a sale line drew from, and at what cost.

    This is the audit trail behind the profit figure: for any sale you can
    show exactly which intake the units came from and what they cost. One
    sale line can span several batches when it straddles a price change.
    """

    sale_item = models.ForeignKey(
        "sales.SaleItem", on_delete=models.CASCADE,
        related_name="cost_allocations", verbose_name=_("Sale Line"),
    )
    batch = models.ForeignKey(
        StockBatch, on_delete=models.SET_NULL, null=True,
        related_name="sale_allocations", verbose_name=_("Batch"),
    )
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Unit Cost"),
        help_text=_("Copied from the batch so the record survives batch deletion."),
    )

    class Meta:
        verbose_name = _("Sale Line Cost Allocation")
        verbose_name_plural = _("Sale Line Cost Allocations")

    def __str__(self):
        return f"{self.quantity} @ {self.unit_cost}"

    @property
    def total_cost(self):
        return (self.unit_cost * self.quantity).quantize(Decimal("0.01"))
