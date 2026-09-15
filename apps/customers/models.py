from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel

from apps.accounts.models import phone_validator


class Customer(OrganizationOwnedModel):
    name = models.CharField(max_length=200, verbose_name=_("Customer Name"), db_index=True)
    phone = models.CharField(
        max_length=20, unique=True, db_index=True, validators=[phone_validator],
        verbose_name=_("Phone"),
        help_text=_("Must be unique — the phone number is how a returning customer "
                    "is identified, so duplicates would split their history and "
                    "loyalty points across two records."),
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    loyalty_points = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0)], verbose_name=_("Loyalty Points")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("customers:customer_detail", kwargs={"pk": self.pk})
