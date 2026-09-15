# NOTE: Submit buttons are rendered in the templates, not via a crispy
# Submit() in the Layout. The `{{ form|crispy }}` *filter* renders fields
# only and silently ignores FormHelper.layout — a Submit() placed here
# would never appear on the page. (The `{% crispy form %}` *tag* honours
# the layout, but emits its own <form> element, which would nest inside
# the <form> our templates already provide.) Keep buttons in templates.
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import MovementType, StockMovement


class StockMovementForm(forms.Form):
    """Plain Form (not ModelForm): quantity_before/after and performed_by
    are computed server-side in the view via apps.inventory.services, not
    submitted by the user — see that module for the actual stock logic."""

    medicine = forms.ModelChoiceField(
        queryset=None, label=_("Medicine"), widget=forms.Select(attrs={"class": "form-select"})
    )
    movement_type = forms.ChoiceField(
        label=_("Movement Type"),
        choices=MovementType.choices,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_movement_type"}),
    )
    quantity = forms.IntegerField(
        label=_("Quantity"),
        min_value=0, widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text=_(
            "For Stock Adjustment, enter the new counted total — not the "
            "difference. 0 is valid here: it writes the whole line off "
            "(e.g. an expired batch that failed at the till and needs "
            "clearing). Stock In, Stock Out and Transfer must move at "
            "least 1 unit."
        ),
    )
    destination = forms.CharField(
        label=_("Destination"),
        required=False, widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text=_("Required for Stock Transfer."),
    )
    reason = forms.CharField(
        label=_("Reason / Notes"),
        required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.medicine.models import Medicine

        self.fields["medicine"].queryset = Medicine.objects.filter(is_active=True).order_by("name")
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("medicine", css_class="col-md-6"),
                Column("movement_type", css_class="col-md-6"),
            ),
            Row(
                Column("quantity", css_class="col-md-6"),
                Column("destination", css_class="col-md-6"),
            ),
            "reason",
        )

    def clean(self):
        cleaned = super().clean()
        movement_type = cleaned.get("movement_type")
        if movement_type == MovementType.TRANSFER and not cleaned.get("destination"):
            self.add_error("destination", _("A destination is required for a stock transfer."))
        # 0 only makes sense for Adjustment (a full write-off to a counted
        # total of zero). For the other three types, "move/receive/send 0
        # units" isn't a real action and is almost always a mis-click.
        if movement_type != MovementType.ADJUSTMENT and cleaned.get("quantity") == 0:
            self.add_error("quantity", _("Quantity must be at least 1 for this movement type."))
        return cleaned


class StockTakeStartForm(forms.Form):
    """Opens a physical count. Branch comes from the request, not the form —
    a person can only ever count the branch they are working in."""

    category = forms.ModelChoiceField(
        queryset=None, required=False, label=_("Category"),
        help_text=_("Count one section at a time, or leave blank for everything."),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        max_length=255, required=False, label=_("Note"),
        widget=forms.TextInput(attrs={"class": "form-control",
                                      "placeholder": _("e.g. month-end count, aisle 1–4")}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.medicine.models import Category

        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["category"].empty_label = str(_("Everything at this branch"))
