from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms
from django.forms import inlineformset_factory

from .models import PurchaseInvoice, PurchaseItem


class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        fields = ["supplier", "purchase_date", "notes"]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)
        self.helper = FormHelper()
        self.helper.form_tag = False  # rendered inside one <form> with the formset
        self.helper.layout = Layout(
            Row(
                Column("supplier", css_class="col-md-6"),
                Column("purchase_date", css_class="col-md-6"),
            ),
            "notes",
        )


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["medicine", "quantity", "purchase_price", "new_selling_price",
                  "discount_percent", "vat_percent"]
        widgets = {
            "medicine": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "purchase_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "new_selling_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01",
                       "placeholder": "optional"}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "vat_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def has_changed(self):
        """An unused extra row (no medicine picked) must be treated as
        blank and skipped — without this override, Django's default
        has_changed() compares discount_percent/vat_percent against their
        non-empty model defaults (0.00 / 15.00), sees a difference from
        the submitted empty string, and wrongly runs full validation on
        an intentionally-empty row, producing spurious "required" errors."""
        if not (self.data and self.data.get(self.add_prefix("medicine"))):
            return False
        return super().has_changed()


# Purchases are immutable once recorded (see models.py docstring), so this
# formset is only ever used at creation time.
#
# `extra=0` with `min_num=1` renders exactly ONE empty row. (Django adds
# min_num + extra forms, so extra=1 here would render two.) The template's
# "+ Add Item" button clones `formset.empty_form` and bumps TOTAL_FORMS, so
# there is no fixed ceiling on line items — the user adds rows as needed.
PurchaseItemFormSet = inlineformset_factory(
    PurchaseInvoice,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
