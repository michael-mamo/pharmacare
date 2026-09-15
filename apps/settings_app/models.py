"""
Pharmacy settings — one row per pharmacy (organization).

Originally a database-backed singleton, predating multi-tenancy: a single
row (`pk` pinned to 1) shared by every pharmacy on the platform, which
meant every pharmacy's sidebar, invoices and reports showed the same
name, logo and tax defaults regardless of which company was actually
logged in. Now scoped to `organization` instead — each pharmacy manages
its own branding independently, and critically, each shows its own name.

`load(organization)` returns that organization's settings row, creating
it (seeded from the organization's own name/currency) on first access.
Platform staff with no organization selected get None back — there is no
sensible "settings" to show when nobody's specific pharmacy is in view.
"""
from decimal import Decimal

from decouple import config
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# Defaults are module-level functions, not lambdas: Django's migration
# serializer cannot serialize a lambda and raises at makemigrations time.
def default_pharmacy_name():
    return config("PHARMACY_NAME", default="PharmaCare Pharmacy")


def default_currency():
    return config("PHARMACY_CURRENCY", default="ETB")


def default_invoice_prefix():
    return config("PHARMACY_INVOICE_PREFIX", default="INV-")


class PharmacySettings(models.Model):
    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE,
        related_name="settings", null=True, blank=True, verbose_name=_("Organization"),
        help_text=_("Blank only for a legacy row that predates per-pharmacy settings."),
    )

    # -- Pharmacy information -------------------------------------------
    name = models.CharField(
        max_length=200, verbose_name=_("Pharmacy Name"),
        default=default_pharmacy_name,
    )
    logo = models.ImageField(
        upload_to="pharmacy/", blank=True, null=True, verbose_name=_("Logo"),
        help_text=_("Shown on invoices and shelf labels."),
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    license_number = models.CharField(
        max_length=80, blank=True, verbose_name=_("Licence Number"),
        help_text=_("Pharmacy operating licence, printed on invoices."),
    )
    tin_number = models.CharField(
        max_length=40, blank=True, verbose_name=_("TIN Number"),
        help_text=_("Taxpayer identification number, printed on invoices."),
    )

    # -- Financial defaults ---------------------------------------------
    currency = models.CharField(
        max_length=10, verbose_name=_("Currency"),
        default=default_currency,
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Default Tax Rate (%)"),
        help_text=_("Pre-filled on new medicines. Existing records keep their own rate."),
        default=Decimal("15.00"),
    )
    large_sale_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("1000.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name=_("Large Sale Alert Threshold"),
        help_text=_("Sales at or above this value raise a notification."),
    )
    loyalty_points_per_unit = models.PositiveIntegerField(
        default=100, verbose_name=_("Currency per Loyalty Point"),
        help_text=_("Amount a customer must spend to earn one loyalty point."),
    )

    # -- Invoice configuration ------------------------------------------
    invoice_prefix = models.CharField(
        max_length=10, verbose_name=_("Invoice Prefix"),
        default=default_invoice_prefix,
        help_text=_("Applied to new invoices only; existing numbers never change."),
    )
    invoice_footer = models.TextField(
        blank=True, verbose_name=_("Invoice Footer"),
        default="Thank you for your purchase.",
        help_text=_("Printed at the bottom of every customer invoice."),
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="settings_updates", verbose_name=_("Updated By"),
    )

    class Meta:
        verbose_name = _("Pharmacy Settings")
        verbose_name_plural = _("Pharmacy Settings")

    def __str__(self):
        return str(self.name)

    @classmethod
    def load(cls, organization):
        if organization is None:
            return None
        obj, created = cls.objects.get_or_create(
            organization=organization,
            defaults={"name": organization.display_name, "currency": organization.currency},
        )
        return obj
