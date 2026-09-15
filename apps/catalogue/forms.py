"""Catalogue forms."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import CatalogueProduct


class RegisterProductForm(forms.Form):
    """Commercial detail for a catalogue product a pharmacy is taking on.

    Identity fields (name, generic name, form, strength, legal class) are
    deliberately absent: they come from the catalogue record and must not be
    editable here, or the standardisation is immediately undone.
    """

    category = forms.ModelChoiceField(
        queryset=None, label=_("Your Category"),
        help_text=_("How you shelve it. The catalogue's own therapeutic category "
                    "is kept separately."),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    supplier = forms.ModelChoiceField(
        queryset=None, required=False, label=_("Supplier"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    purchase_price = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, label=_("Purchase Price"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    selling_price = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, label=_("Selling Price"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    quantity = forms.IntegerField(
        min_value=0, initial=0, label=_("Opening Quantity"),
        help_text=_("Goes to the main branch. Prefer recording a purchase instead, "
                    "so the cost is tracked properly."),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    reorder_level = forms.IntegerField(
        min_value=0, initial=10, label=_("Reorder Level"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    expiry_date = forms.DateField(
        required=False, label=_("Expiry Date"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    batch_number = forms.CharField(
        max_length=60, required=False, label=_("Batch Number"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    tax_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, required=False,
        label=_("VAT (%)"),
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def __init__(self, *args, catalogue_product=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.medicine.models import Category
        from apps.suppliers.models import Supplier

        self.catalogue_product = catalogue_product
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["supplier"].queryset = Supplier.objects.order_by("name")

        # Devices have no shelf life; everything else must have a date.
        if catalogue_product is not None and catalogue_product.product_type != "DEVICE":
            self.fields["expiry_date"].required = True

    def clean_selling_price(self):
        selling = self.cleaned_data.get("selling_price")
        purchase = self.data.get("purchase_price")
        try:
            purchase = float(purchase)
        except (TypeError, ValueError):
            return selling
        # A warning rather than a hard error: clearance and loss-leader pricing
        # are legitimate, so this is the pharmacy's decision to make knowingly.
        if selling is not None and float(selling) < purchase:
            self.add_error(
                "selling_price",
                _("This is below the purchase price, so every sale would lose "
                  "money. Change it, or confirm it is deliberate by entering it "
                  "again.") if not self.data.get("confirm_loss") else None,
            )
        return selling


class CatalogueProductForm(forms.ModelForm):
    """For adding a product the catalogue does not yet contain."""

    class Meta:
        model = CatalogueProduct
        fields = [
            "generic_name", "brand_name", "strength", "dosage_form", "route",
            "atc_code", "category", "schedule", "product_type", "default_unit",
            "pack_size", "manufacturer", "country_of_origin",
            "efda_registration_number", "barcode", "is_essential",
            "requires_cold_chain", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
        self.fields["efda_registration_number"].help_text = _(
            "Only fill this in from the EFDA register. Leave blank if you do not "
            "have the number — a wrong registration number is worse than none."
        )
