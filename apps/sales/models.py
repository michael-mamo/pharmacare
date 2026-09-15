"""
Sales / POS models: a Sale (invoice header) with SaleItem line items.

Design notes
------------
- Mirrors the Purchase structure from Phase 3, but in the opposite
  direction: each SaleItem *reduces* the medicine's stock on save.
- Prices are **snapshotted** onto each SaleItem at the moment of sale
  (unit_price, tax_percent, discount_percent). This is deliberate and
  important: if a medicine's selling price changes next month, historical
  invoices must still show what the customer actually paid. Never
  recompute a past invoice from the current Medicine row.
- Like purchases, a completed sale is an immutable financial record. There
  is no edit; a mistake is corrected by voiding (which returns stock),
  restricted to Administrator — see User.can_void_sales().
- Stock is decremented inside the same transaction as the invoice (see
  apps.sales.services.complete_sale), with row locking, so two cashiers
  ringing up the last packet at the same moment can't oversell it.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.medicine.models import Medicine


class PaymentMethod(models.TextChoices):
    CASH = "CASH", _("Cash")
    CARD = "CARD", _("Card")
    MOBILE_MONEY = "MOBILE", _("Mobile Money")


class SaleStatus(models.TextChoices):
    COMPLETED = "COMPLETED", _("Completed")
    VOIDED = "VOIDED", _("Voided")


class Sale(OrganizationOwnedModel):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.PROTECT, null=True, blank=True,
        related_name="sales", verbose_name=_("Branch"),
        help_text=_("Which branch made this sale. Nullable only so rows recorded "
                    "before multi-branch support remain valid."),
    )
    invoice_number = models.CharField(
        max_length=24, unique=True, editable=False, verbose_name=_("Invoice Number"),
        help_text=_("Auto-generated on save using the configured invoice prefix."),
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales", verbose_name=_("Customer"),
        help_text=_("Optional — walk-in sales can be recorded without a customer."),
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH,
        verbose_name=_("Payment Method"),
    )
    status = models.CharField(
        max_length=10, choices=SaleStatus.choices, default=SaleStatus.COMPLETED,
        db_index=True, verbose_name=_("Status"),
    )
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Amount Paid"),
    )
    served_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales", verbose_name=_("Served By"),
    )
    voided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="voided_sales", verbose_name=_("Voided By"),
    )
    voided_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Voided At"))
    void_reason = models.CharField(max_length=255, blank=True, verbose_name=_("Void Reason"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Date"))

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["branch", "-created_at"]),
        ]

    def __str__(self):
        return self.invoice_number

    def get_absolute_url(self):
        return reverse("sales:sale_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.invoice_number:
            from decouple import config

            # A branch may define its own prefix so invoice numbers from
            # different branches are never confused with each other.
            prefix = ""
            if self.branch_id and self.branch.invoice_prefix:
                prefix = self.branch.invoice_prefix
            if not prefix:
                prefix = config("PHARMACY_INVOICE_PREFIX", default="INV-")
            self.invoice_number = f"{prefix}{self.pk:06d}"
            super().save(update_fields=["invoice_number"])

    # ---- Money totals (computed from snapshotted line values) -------------
    @property
    def subtotal(self):
        return sum((i.line_subtotal for i in self.items.all()), Decimal("0.00"))

    @property
    def total_discount(self):
        return sum((i.line_discount for i in self.items.all()), Decimal("0.00"))

    @property
    def total_vat(self):
        return sum((i.line_vat for i in self.items.all()), Decimal("0.00"))

    @property
    def grand_total(self):
        return sum((i.line_total for i in self.items.all()), Decimal("0.00"))

    @property
    def change_due(self):
        change = self.amount_paid - self.grand_total
        return change if change > 0 else Decimal("0.00")

    @property
    def total_units(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def total_cost(self):
        """Cost of goods sold for this invoice, from the consumed batches."""
        return sum((i.line_cost for i in self.items.all()), Decimal("0.00"))

    @property
    def gross_profit(self):
        return sum((i.line_profit for i in self.items.all()), Decimal("0.00"))

    @property
    def is_voided(self):
        return self.status == SaleStatus.VOIDED


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(
        Medicine, on_delete=models.PROTECT, related_name="sale_items", verbose_name=_("Medicine")
    )
    # Snapshot of the medicine's name at sale time, so an invoice stays
    # readable even if the catalog entry is later renamed.
    medicine_name = models.CharField(max_length=200, verbose_name=_("Medicine"))
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Quantity")
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Unit Price"),
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Discount (%)"),
    )
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("VAT (%)"),
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))], verbose_name=_("Unit Cost"),
        help_text=_("Actual weighted cost of the units dispensed, taken from the "
                    "batches consumed (FEFO). Fixed at the time of sale, so a "
                    "later purchase at a different price cannot change past profit."),
    )

    class Meta:
        verbose_name = _("Sale Item")
        verbose_name_plural = _("Sale Items")

    def __str__(self):
        return f"{self.medicine_name} x{self.quantity}"

    @property
    def line_subtotal(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    @property
    def line_discount(self):
        return (self.line_subtotal * self.discount_percent / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def line_after_discount(self):
        return (self.line_subtotal - self.line_discount).quantize(Decimal("0.01"))

    @property
    def line_vat(self):
        return (self.line_after_discount * self.tax_percent / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def line_total(self):
        return (self.line_after_discount + self.line_vat).quantize(Decimal("0.01"))

    @property
    def line_cost(self):
        """Cost of goods for this line, at the batches actually consumed."""
        return (self.unit_cost * self.quantity).quantize(Decimal("0.01"))

    @property
    def line_profit(self):
        """Gross profit: what the customer paid net of VAT, minus true cost.
        VAT is excluded because it is collected on behalf of the tax
        authority — it was never the pharmacy's margin."""
        return (self.line_after_discount - self.line_cost).quantize(Decimal("0.01"))

    @property
    def line_margin_percent(self):
        base = self.line_after_discount
        if not base:
            return Decimal("0.00")
        return (self.line_profit / base * Decimal("100")).quantize(Decimal("0.1"))
