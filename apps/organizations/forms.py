"""Organization (pharmacy tenant) management forms — platform staff only."""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms

from .models import Organization, SubscriptionPlan


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "legal_name", "trade_name", "tin", "license_number",
            "phone", "email", "region", "city", "address",
            "currency", "default_language", "logo",
            "status", "plan", "plan_notes", "subscription_ends_at",
            "max_branches", "max_users",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "subscription_ends_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.setdefault("class", "form-control")
            else:
                field.widget.attrs.setdefault("class", "form-control")
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("legal_name", css_class="col-md-6"),
                Column("trade_name", css_class="col-md-6"),
            ),
            Row(
                Column("tin", css_class="col-md-6"),
                Column("license_number", css_class="col-md-6"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("region", css_class="col-md-6"),
                Column("city", css_class="col-md-6"),
            ),
            "address",
            Row(
                Column("currency", css_class="col-md-6"),
                Column("default_language", css_class="col-md-6"),
            ),
            "logo",
            Row(
                Column("status", css_class="col-md-6"),
                Column("plan", css_class="col-md-6"),
            ),
            "plan_notes",
            Row(
                Column("subscription_ends_at", css_class="col-md-4"),
                Column("max_branches", css_class="col-md-4"),
                Column("max_users", css_class="col-md-4"),
            ),
        )


class RecordPaymentForm(forms.Form):
    """Manually records a payment today; a future Chapa webhook creates the
    same underlying Payment row programmatically instead — see
    record_payment() in apps.organizations.models."""

    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    plan = forms.ChoiceField(choices=SubscriptionPlan.choices)
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="The organization's subscription end date is set to this on save.",
    )
    notes = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={"placeholder": 'e.g. "Bank transfer, receipt #1234"'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
        self.helper = FormHelper()
        self.helper.form_tag = False
