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

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address", "loyalty_points"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_phone(self):
        """Normalise before the uniqueness check so "0911 22 33 44" and
        "0911223344" are recognised as the same customer, and return a
        message that names the existing record rather than a bare
        "already exists"."""
        phone = (self.cleaned_data.get("phone") or "").strip()
        normalised = phone.replace(" ", "").replace("-", "")

        existing = Customer.objects.filter(phone=normalised)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        match = existing.first()
        if match:
            raise forms.ValidationError(
                _('A customer with this phone number already exists: "%(name)s". '
                  "Open that record instead of creating a duplicate.")
                % {"name": match.name}
            )
        return normalised

    def __init__(self, *args, **kwargs):
        # Only Administrators/Store Managers may hand-adjust loyalty points;
        # everyone else registers/edits a customer without touching them.
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        if user and not (user.is_administrator or user.is_store_manager):
            del self.fields["loyalty_points"]

        layout_fields = [
            Row(Column("name", css_class="col-md-6"), Column("phone", css_class="col-md-6")),
            Row(Column("email", css_class="col-md-6"),
                Column("loyalty_points", css_class="col-md-6") if "loyalty_points" in self.fields else Column(css_class="col-md-6")),
            "address",
        ]
        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_fields)
