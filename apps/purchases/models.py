"""
Purchase models: a PurchaseInvoice (header) with one or more PurchaseItem
line items — matching how a real supplier invoice is structured, while
still covering every field the spec calls for (Purchase Number, Supplier,
Purchase Date, Medicine, Quantity, Purchase Price, Discount, VAT, Total).

Design notes
------------
- Purchases are treated as an append-only financial ledger: once recorded,
  an invoice cannot be edited, only deleted (Administrator only — see
  apps.accounts.models.User.can_delete_purchases). This mirrors standard
  accounting practice (corrections are new entries, not silent edits) and
  keeps "what increased this medicine's stock, and when" fully auditable.
- Stock increase happens exactly once, at PurchaseItem creation, inside
  the same DB transaction as the invoice — see PurchaseItem.save().
  Deleting an invoice reverses the effect (see views.PurchaseDeleteView).
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel

from apps.accounts.models import User
from apps.medicine.models import Medicine
from apps.suppliers.models import Supplier


class PurchaseInvoice(OrganizationOwnedModel):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.PROTECT, null=True, blank=True,
        related_name="purchase_invoices", verbose_name=_("Receiving Branch"),
        help_text=_("The branch these goods were delivered to. Stock is added there."),
    )
    purchase_number = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name=_("Purchase Number"),
        help_text=_("Auto-generated on save (e.g. PUR-000001)."),
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_invoices", verbose_name=_("Supplier")
    )
    purchase_date = models.DateField(verbose_name=_("Purchase Date"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_invoices", verbose_name=_("Recorded By"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Purchase Invoice")
        verbose_name_plural = _("Purchase Invoices")
        ordering = ["-purchase_date", "-created_at"]

    def __str__(self):
        return self.purchase_number

    def get_absolute_url(self):
        return reverse("purchases:purchase_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.purchase_number:
            self.purchase_number = f"PUR-{self.pk:06d}"
            super().save(update_fields=["purchase_number"])

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def total_items(self):
        return self.items.count()


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(
        Medicine, on_delete=models.PROTECT, related_name="purchase_items", verbose_name=_("Medicine")
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Quantity")
    )
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Purchase Price"), help_text=_("Unit cost price for this line."),
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Discount (%)"),
    )
    vat_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("VAT (%)"),
    )
    new_selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("New Selling Price"),
        help_text=_("Optional. If this intake changes what you charge, set the "
                    "new price here — it updates the medicine's current price. "
                    "Sales already made keep the price they were sold at."),
    )
    # Snapshot so historical invoices remain accurate even if quantity is
    # later reversed by a delete — see PurchaseItem.delete().
    stock_applied = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = _("Purchase Item")
        verbose_name_plural = _("Purchase Items")

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity} ({self.purchase.purchase_number})"

    @property
    def line_subtotal(self):
        return (self.purchase_price * self.quantity).quantize(Decimal("0.01"))

    @property
    def line_total(self):
        discounted = self.line_subtotal * (Decimal("1") - self.discount_percent / Decimal("100"))
        return (discounted * (Decimal("1") + self.vat_percent / Decimal("100"))).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        """Creates a stock batch exactly once, the first time this line is
        saved. The batch carries this purchase's own unit cost, so a later
        purchase at a different price cannot rewrite the cost of these
        units — see apps/inventory/batches.py for why that matters.

        Subsequent saves (there shouldn't be any: purchases are immutable —
        see the module docstring) won't double-count.
        """
        from apps.inventory.allocation import ensure_opening_batch, receive_batch

        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.stock_applied:
            medicine = Medicine.objects.select_for_update().get(pk=self.medicine_id)
            # Goods land at the branch that received the delivery, not at some
            # pharmacy-wide pool.
            branch = self.purchase.branch
            ensure_opening_batch(medicine, branch=branch)
            receive_batch(
                branch=branch,
                ledger_source="PURCHASE",
                reference=self.purchase.purchase_number,
                medicine=medicine,
                quantity=self.quantity,
                unit_cost=self.purchase_price,
                expiry_date=medicine.expiry_date,
                batch_number=medicine.batch_number or "",
                purchase_item=self,
                source="PURCHASE",
                selling_price=self.new_selling_price or medicine.selling_price,
            )
            # An intake may change what we charge going forward. Historical
            # sales are unaffected: each SaleItem snapshots its own price.
            update_fields = []
            if self.new_selling_price and self.new_selling_price != medicine.selling_price:
                medicine.selling_price = self.new_selling_price
                update_fields.append("selling_price")
            # Keep the headline cost in step with the latest intake so the
            # medicine form shows a sensible current figure; actual costing
            # always comes from the batches, never from this field.
            if medicine.purchase_price != self.purchase_price:
                medicine.purchase_price = self.purchase_price
                update_fields.append("purchase_price")
            if update_fields:
                medicine.save(update_fields=update_fields)

            self.stock_applied = True
            super().save(update_fields=["stock_applied"])

    def delete(self, *args, **kwargs):
        """Reverse the stock effect before removing the line item, so
        deleting a purchase invoice never leaves phantom stock behind.

        Only the units still unsold are removed. If some were already
        dispensed, those batches are left alone — clawing back sold stock
        would corrupt both the count and the recorded cost of those sales.
        """
        if self.stock_applied:
            medicine = Medicine.objects.filter(pk=self.medicine_id).first()
            removed = 0
            branch = self.purchase.branch
            for batch in self.batches.all():
                take = batch.quantity_remaining
                if take:
                    batch.quantity_remaining = 0
                    batch.save(update_fields=["quantity_remaining"])
                    removed += take
            if medicine and removed:
                from apps.branches.models import BranchStock

                from apps.inventory.allocation import _adjust_branch_stock
                from apps.inventory.stocktake import LedgerSource

                _adjust_branch_stock(
                    branch, medicine, -removed,
                    source=LedgerSource.PURCHASE_DELETE,
                    reference=self.purchase.purchase_number,
                    note="Unsold units removed when the purchase was deleted",
                )
        super().delete(*args, **kwargs)
