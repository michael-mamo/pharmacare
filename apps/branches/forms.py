"""Branch forms."""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role, User

from .models import Branch, BranchStock


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            "name", "phone", "email", "city", "address",
            "license_number", "invoice_prefix", "manager",
            "is_main", "is_active", "opened_on",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "opened_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only Store Managers and Administrators can sensibly run a branch.
        self.fields["manager"].queryset = User.objects.filter(
            is_active=True, role__in=[Role.STORE_MANAGER, Role.ADMINISTRATOR]
        ).order_by("first_name", "username")
        self.fields["manager"].required = False
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column("name", css_class="col-md-8"), Column("opened_on", css_class="col-md-4")),
            Row(Column("phone", css_class="col-md-4"), Column("email", css_class="col-md-4"),
                Column("city", css_class="col-md-4")),
            "address",
            Row(Column("license_number", css_class="col-md-4"),
                Column("invoice_prefix", css_class="col-md-4"),
                Column("manager", css_class="col-md-4")),
            Row(Column("is_main", css_class="col-md-6"), Column("is_active", css_class="col-md-6")),
        )

    def clean_is_active(self):
        active = self.cleaned_data.get("is_active")
        # Deactivating the main branch would leave Administrators with no
        # default branch to land on, so require the flag to move first.
        if not active and self.instance.pk and self.instance.is_main:
            raise forms.ValidationError(
                _("The main branch cannot be deactivated. Make another branch the "
                  "main one first.")
            )
        return active


class BranchStockForm(forms.ModelForm):
    """Edits the per-branch reorder level and shelf location.

    Quantity is deliberately excluded: stock must only change through a
    purchase, a sale, or a recorded stock movement, so that every change has
    an audit trail and the batch ledger stays in step.
    """

    class Meta:
        model = BranchStock
        fields = ["reorder_level", "shelf_location"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class TransferForm(forms.Form):
    """Moves stock from the current branch to another."""

    medicine = forms.ModelChoiceField(
        queryset=None, label=_("Product"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    destination_branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(), label=_("Destination Branch"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    quantity = forms.IntegerField(
        min_value=1, label=_("Quantity"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    reason = forms.CharField(
        max_length=255, required=False, label=_("Reason / Notes"),
        widget=forms.TextInput(attrs={"class": "form-control",
                                      "placeholder": _("e.g. restocking Bole from main store")}),
    )

    def __init__(self, *args, source_branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.medicine.models import Medicine

        self.source_branch = source_branch
        # Only offer products this branch actually holds — offering the whole
        # catalogue would invite a transfer that fails on submit.
        if source_branch is not None:
            self.fields["medicine"].queryset = Medicine.objects.filter(
                branch_stocks__branch=source_branch, branch_stocks__quantity__gt=0
            ).distinct().order_by("name")
            self.fields["destination_branch"].queryset = Branch.objects.filter(
                is_active=True
            ).exclude(pk=source_branch.pk).order_by("name")
        else:
            self.fields["medicine"].queryset = Medicine.objects.none()

    def clean(self):
        cleaned = super().clean()
        medicine = cleaned.get("medicine")
        quantity = cleaned.get("quantity")
        if medicine and quantity and self.source_branch:
            available = medicine.stock_at(self.source_branch)
            if quantity > available:
                self.add_error("quantity", _(
                    "Only %(have)s in stock at %(branch)s."
                ) % {"have": available, "branch": self.source_branch.name})
        return cleaned
