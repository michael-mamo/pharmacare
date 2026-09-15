# NOTE: Submit buttons are rendered in the templates, not via a crispy
# Submit() in the Layout. The `{{ form|crispy }}` *filter* renders fields
# only and silently ignores FormHelper.layout — a Submit() placed here
# would never appear on the page. (The `{% crispy form %}` *tag* honours
# the layout, but emits its own <form> element, which would nest inside
# the <form> our templates already provide.) Keep buttons in templates.
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Category, Medicine


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "name", "description",
        )


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "catalogue_product",
            "product_type",
            "name", "generic_name", "brand", "category", "supplier",
            "barcode", "batch_number", "manufacturing_date", "expiry_date",
            "purchase_price", "selling_price", "tax_percent", "discount_percent",
            "quantity", "reorder_level", "unit",
            "description", "image", "requires_prescription", "is_active",
        ]
        widgets = {
            "manufacturing_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        # Cost/purchase price is commercially sensitive — only shown on this
        # form to roles that are allowed to see it at all (Administrator /
        # Store Manager). The view layer already blocks Pharmacist/Cashier
        # from reaching create/edit entirely, but this keeps the form
        # correct even if reused elsewhere.
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and not user.can_view_cost_price():
            del self.fields["purchase_price"]

        # Only offer catalogue entries this pharmacy hasn't already
        # registered (plus whichever one this item is already linked to,
        # when editing) — Medicine.clean() rejects a duplicate anyway, but
        # there's no reason to let someone pick a taken entry in the first
        # place. Required, in effect, for product_type=MEDICINE; enforced
        # in Medicine.clean() rather than here so it holds everywhere
        # (Django admin, imports, this form) and not just in this view.
        from apps.catalogue.models import CatalogueProduct

        self.fields["catalogue_product"].queryset = (
            CatalogueProduct.objects.filter(is_active=True)
            .filter(Q(medicines__isnull=True) | Q(pk=self.instance.catalogue_product_id))
            .distinct()
            .order_by("generic_name", "strength")
        )
        self.fields["catalogue_product"].help_text = _(
            "Strongly recommended for Medicine — search and pick the standard entry "
            "this stock item is, so it matches the same medicine at every pharmacy in "
            "reporting. If it genuinely isn't listed, you can leave this blank and "
            "type the name yourself below — it will just be flagged as Not "
            "Standardised. Once linked, the name and generic name below are locked "
            "to whatever the catalogue entry says."
        )
        # Name/generic name are only genuinely optional at the form level
        # when a catalogue link is going to supply them — Medicine.clean()
        # fills them in from the catalogue record before its own "required"
        # check runs. But that's a model-level check, which happens *after*
        # the form's own per-field validation; if these stayed required
        # here, submitting with a catalogue link and a blank Name would
        # never even reach the model layer to get filled in. The form's
        # own clean() below re-imposes "required" for the case that
        # genuinely still needs it: no catalogue link at all.
        self.fields["name"].required = False
        self.fields["generic_name"].required = False

        for name, field in self.fields.items():
            if name in ("is_active", "requires_prescription"):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

        price_row = (
            Row(
                Column("purchase_price", css_class="col-md-4") if "purchase_price" in self.fields else Column(css_class="col-md-4"),
                Column("selling_price", css_class="col-md-4"),
                Column("tax_percent", css_class="col-md-2"),
                Column("discount_percent", css_class="col-md-2"),
            )
        )

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column("catalogue_product", css_class="col-md-12")),
            Row(Column("product_type", css_class="col-md-6"),
                Column("name", css_class="col-md-6")),
            Row(Column("generic_name", css_class="col-md-6"),
                Column("brand", css_class="col-md-6")),
            Row(Column("barcode", css_class="col-md-6"),
                Column("batch_number", css_class="col-md-6")),
            Row(Column("category", css_class="col-md-6"), Column("supplier", css_class="col-md-6")),
            Row(Column("manufacturing_date", css_class="col-md-6"),
                Column("expiry_date", css_class="col-md-6")),
            price_row,
            Row(Column("quantity", css_class="col-md-4"),
                Column("reorder_level", css_class="col-md-4"),
                Column("unit", css_class="col-md-4")),
            "description", "image", "requires_prescription", "is_active",
        )

    def clean(self):
        cleaned = super().clean()
        # The one case Name still has to be typed by hand: nothing is
        # linked to fill it in. (product_type == MEDICINE with no link is
        # already rejected by Medicine.clean() with its own message; this
        # covers every non-medicine type, where a catalogue link is never
        # offered in the first place.)
        if not cleaned.get("catalogue_product") and not cleaned.get("name"):
            self.add_error("name", _("Required unless a catalogue entry is linked above."))
        return cleaned
