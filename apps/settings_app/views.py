"""
Pharmacy settings views — Administrator only (see User.can_manage_settings).

Includes the database backup action from the spec. Backup behaviour differs
by engine, and that difference is handled explicitly rather than pretending
one command fits both:

  * SQLite (development)  — streams the database file itself, which is a
    complete and directly restorable backup.
  * PostgreSQL (production) — a real backup needs `pg_dump`, which is a
    server-side operation with its own credentials and retention policy. The
    view refuses to fake it and instead tells the administrator exactly what
    to run, because a download button that silently produced an incomplete
    dump would be worse than no button at all.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row
from django import forms
from django.conf import settings as django_settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView, View

from apps.accounts.permissions import AdministratorRequiredMixin

from .models import PharmacySettings


class PharmacySettingsForm(forms.ModelForm):
    class Meta:
        model = PharmacySettings
        fields = [
            "name", "logo", "phone", "email", "address",
            "license_number", "tin_number",
            "currency", "tax_rate", "large_sale_threshold", "loyalty_points_per_unit",
            "invoice_prefix", "invoice_footer",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "invoice_footer": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column("name", css_class="col-md-8"), Column("logo", css_class="col-md-4")),
            Row(Column("phone", css_class="col-md-6"), Column("email", css_class="col-md-6")),
            "address",
            Row(Column("license_number", css_class="col-md-6"),
                Column("tin_number", css_class="col-md-6")),
            Row(Column("currency", css_class="col-md-3"),
                Column("tax_rate", css_class="col-md-3"),
                Column("large_sale_threshold", css_class="col-md-3"),
                Column("loyalty_points_per_unit", css_class="col-md-3")),
            Row(Column("invoice_prefix", css_class="col-md-4"),
                Column("invoice_footer", css_class="col-md-8")),
        )


class PharmacySettingsUpdateView(AdministratorRequiredMixin, UpdateView):
    model = PharmacySettings
    form_class = PharmacySettingsForm
    template_name = "settings_app/settings_form.html"
    success_url = reverse_lazy("settings_app:settings")

    def dispatch(self, request, *args, **kwargs):
        # Platform staff who haven't switched into a pharmacy have no
        # organization to load settings for — there's nothing sensible to
        # show here until they pick one.
        if getattr(request, "organization", None) is None:
            messages.error(request, "Switch into a pharmacy first to manage its settings.")
            return redirect("organizations:list")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return PharmacySettings.load(self.request.organization)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Pharmacy settings saved.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engine = django_settings.DATABASES["default"]["ENGINE"]
        context["db_engine"] = engine
        context["is_sqlite"] = engine.endswith("sqlite3")
        context["db_name"] = str(django_settings.DATABASES["default"]["NAME"])
        return context


class DatabaseBackupView(AdministratorRequiredMixin, View):
    """Downloads a database backup. SQLite only — see module docstring for
    why PostgreSQL is redirected to pg_dump rather than faked here."""

    def post(self, request):
        db = django_settings.DATABASES["default"]
        engine = db["ENGINE"]

        if not engine.endswith("sqlite3"):
            messages.warning(
                request,
                "This deployment uses PostgreSQL. Browser-based backup is "
                "intentionally disabled because a valid dump requires "
                "pg_dump on the database server. Run: "
                f"pg_dump -U <user> -d {db.get('NAME', 'pharmacare')} "
                "-F c -f pharmacare-backup.dump",
            )
            return self.redirect_back()

        path = db["NAME"]
        try:
            handle = open(path, "rb")
        except OSError:
            raise Http404("Database file not found.")

        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        response = FileResponse(handle, as_attachment=True,
                                filename=f"pharmacare-backup-{stamp}.sqlite3")
        return response

    def redirect_back(self):
        from django.shortcuts import redirect

        return redirect("settings_app:settings")
