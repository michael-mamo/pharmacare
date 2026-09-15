from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import OrganizationOwnedModel

from apps.accounts.models import phone_validator


class Supplier(OrganizationOwnedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=200, verbose_name=_("Supplier Name"), db_index=True)
    contact_person = models.CharField(max_length=150, blank=True, verbose_name=_("Contact Person"))
    phone = models.CharField(max_length=20, validators=[phone_validator], verbose_name=_("Phone"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name=_("Status"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("suppliers:supplier_detail", kwargs={"pk": self.pk})

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def medicine_count(self):
        return self.medicines.count()
