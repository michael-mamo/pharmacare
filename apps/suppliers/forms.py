# NOTE: Submit buttons are rendered in the templates, not via a crispy
# Submit() in the Layout. The `{{ form|crispy }}` *filter* renders fields
# only and silently ignores FormHelper.layout — a Submit() placed here
# would never appear on the page. (The `{% crispy form %}` *tag* honours
# the layout, but emits its own <form> element, which would nest inside
# the <form> our templates already provide.) Keep buttons in templates.
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms

from .models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone", "email", "address", "status"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="col-md-6"),
                Column("contact_person", css_class="col-md-6"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            "address",
            "status",
        )
