"""
StockMovement records any manual change to a medicine's quantity that
does NOT come from a Purchase (which already adjusts stock itself) or a
Sale (Phase 4, which will reduce stock at the point of sale). This covers:

  - STOCK_IN:     found/received stock not tied to a purchase invoice
                   (e.g. a correction, a donation, a manufacturer sample)
  - STOCK_OUT:    stock leaving for a reason other than a sale
                   (breakage, spillage, internal use, expiry write-off)
  - ADJUSTMENT:   a stocktake correction — the user enters the *actual*
                   counted quantity and the system computes the delta
  - TRANSFER:     stock leaving for another branch/location. This project
                   does not yet model branches/locations (out of scope for
                   the current spec), so a transfer is recorded as stock
                   leaving this pharmacy with a free-text destination —
                   sufficient for a single-location deployment, and the
                   `destination` field gives a natural upgrade path to a
                   proper Location model later without a data migration.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.medicine.models import Medicine


class MovementType(models.TextChoices):
    STOCK_IN = "IN", _("Stock In")
    STOCK_OUT = "OUT", _("Stock Out")
    ADJUSTMENT = "ADJUSTMENT", _("Stock Adjustment")
    TRANSFER = "TRANSFER", _("Stock Transfer")


class StockMovement(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.PROTECT, null=True, blank=True,
        related_name="stock_movements", verbose_name=_("Branch"),
        help_text=_("The branch whose stock this movement affects."),
    )
    medicine = models.ForeignKey(
        Medicine, on_delete=models.CASCADE, related_name="stock_movements", verbose_name=_("Medicine")
    )
    movement_type = models.CharField(
        max_length=12, choices=MovementType.choices, verbose_name=_("Movement Type"), db_index=True
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Quantity"),
        help_text=_("For Stock Adjustment, this is the new counted quantity, not a delta."),
    )
    quantity_before = models.PositiveIntegerField(editable=False, verbose_name=_("Quantity Before"))
    quantity_after = models.PositiveIntegerField(editable=False, verbose_name=_("Quantity After"))
    destination_branch = models.ForeignKey(
        "branches.Branch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incoming_transfers", verbose_name=_("Destination Branch"),
        help_text=_("For a Stock Transfer: the branch receiving the goods. Stock is "
                    "removed here and added there in one operation, at the same cost."),
    )
    destination = models.CharField(
        max_length=200, blank=True, verbose_name=_("Destination"),
        help_text=_("Required for Stock Transfer — the receiving branch or location."),
    )
    reason = models.CharField(max_length=255, blank=True, verbose_name=_("Reason / Notes"))
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_movements", verbose_name=_("Performed By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["movement_type"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return f"{self.get_movement_type_display()} — {self.medicine.name} ({self.created_at:%Y-%m-%d})"

    def get_absolute_url(self):
        return reverse("inventory:movement_list")

    @property
    def delta(self):
        return self.quantity_after - self.quantity_before


# ---------------------------------------------------------------------------
# Batch-level costing lives in batches.py for readability; re-exported here
# so Django's app registry discovers the models.
# ---------------------------------------------------------------------------
from .batches import SaleItemCost, StockBatch  # noqa: E402,F401
from .stocktake import (  # noqa: E402,F401
    LedgerSource, StockLedger, StockTake, StockTakeLine, StockTakeStatus,
)
