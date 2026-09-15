"""
Catalogue views.

The standard catalogue is shared platform reference data (see
Organization's docstring) — not any one pharmacy's business data — so it
is managed by platform staff only, same as organizations themselves. A
pharmacy still *uses* catalogue data every time someone links a Medicine
to a catalogue entry on the ordinary Add Medicine form; what's restricted
here is browsing/administering the catalogue as its own section, which no
pharmacy — including its own Administrator — needs to do.
"""
import io
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView
from django.utils.translation import gettext as _

from apps.accounts.permissions import PlatformStaffRequiredMixin

from .forms import CatalogueProductForm, RegisterProductForm
from .models import CatalogueCategory, CatalogueProduct, DosageForm, ScheduleClass
from .services import catalogue_coverage, register_product


class SeedCatalogueTriggerView(LoginRequiredMixin, View):
    """Runs `seed_catalogue --overwrite` from inside the deployment itself.

    A stopgap for serverless hosts (Vercel) where nobody has a shell against
    the production database, and for a local network that blocks outbound
    port 5432 to Neon — Vercel's own servers can always reach the database,
    since that's how every ordinary page load works.

    Double-gated: needs BOTH a platform staff session AND a token matching
    the SEED_TRIGGER_TOKEN environment variable. Delete this view (or unset
    the env var) once you've used it — it's a one-time migration aid, not
    something to leave wired up permanently.
    """

    def get(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_platform_staff()):
            return HttpResponseForbidden("Platform administrator access required.")
        expected = os.environ.get("SEED_TRIGGER_TOKEN")
        if not expected or request.GET.get("token") != expected:
            return HttpResponseForbidden("Missing or incorrect token.")
        buffer = io.StringIO()
        call_command("seed_catalogue", overwrite=True, stdout=buffer)
        return HttpResponse(buffer.getvalue(), content_type="text/plain")


class CatalogueListView(PlatformStaffRequiredMixin, ListView):
    model = CatalogueProduct
    template_name = "catalogue/product_list.html"
    context_object_name = "products"
    paginate_by = 30

    def get_queryset(self):
        qs = CatalogueProduct.objects.filter(is_active=True).select_related(
            "category"
        ).prefetch_related("medicines")
        query = self.request.GET.get("q")
        category = self.request.GET.get("category")
        schedule = self.request.GET.get("schedule")
        form = self.request.GET.get("form")
        status = self.request.GET.get("status")
        if query:
            qs = (qs.filter(generic_name__icontains=query)
                  | qs.filter(brand_name__icontains=query)
                  | qs.filter(atc_code__icontains=query)
                  | qs.filter(barcode=query)).filter(is_active=True)
        if category:
            qs = qs.filter(category_id=category)
        if schedule:
            qs = qs.filter(schedule=schedule)
        if form:
            qs = qs.filter(dosage_form=form)
        if status == "registered":
            qs = qs.filter(medicines__isnull=False)
        elif status == "unregistered":
            qs = qs.filter(medicines__isnull=True)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = CatalogueCategory.objects.all()
        context["schedules"] = ScheduleClass.choices
        context["forms"] = DosageForm.choices
        context["coverage"] = catalogue_coverage()
        context["can_manage"] = self.request.user.can_manage_catalog()
        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "category": self.request.GET.get("category", ""),
            "schedule": self.request.GET.get("schedule", ""),
            "form": self.request.GET.get("form", ""),
            "status": self.request.GET.get("status", ""),
        }
        return context


class CatalogueDetailView(PlatformStaffRequiredMixin, DetailView):
    model = CatalogueProduct
    template_name = "catalogue/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registered"] = self.object.medicines.select_related("category").first()
        context["can_manage"] = self.request.user.can_manage_catalog()
        return context


class RegisterProductView(PlatformStaffRequiredMixin, View):
    """Turns a catalogue record into a stock item.

    Platform-only, like the rest of this module. A pharmacy adds a
    catalogue-linked medicine through the ordinary Add Medicine form's
    catalogue picker instead — see MedicineForm.
    """

    def get(self, request, pk):
        product = get_object_or_404(CatalogueProduct, pk=pk, is_active=True)
        form = RegisterProductForm(catalogue_product=product)
        return render(request, "catalogue/register.html",
                      {"product": product, "form": form})

    def post(self, request, pk):
        product = get_object_or_404(CatalogueProduct, pk=pk, is_active=True)
        form = RegisterProductForm(request.POST, catalogue_product=product)
        if form.is_valid():
            try:
                medicine = register_product(
                    catalogue_product=product,
                    category=form.cleaned_data["category"],
                    supplier=form.cleaned_data.get("supplier"),
                    purchase_price=form.cleaned_data["purchase_price"],
                    selling_price=form.cleaned_data["selling_price"],
                    quantity=form.cleaned_data["quantity"],
                    reorder_level=form.cleaned_data["reorder_level"],
                    expiry_date=form.cleaned_data.get("expiry_date"),
                    batch_number=form.cleaned_data.get("batch_number", ""),
                    tax_percent=form.cleaned_data.get("tax_percent"),
                    user=request.user,
                )
            except ValidationError as e:
                for message in e.messages:
                    form.add_error(None, message)
            else:
                messages.success(request, _(
                    "%(name)s registered as %(code)s, linked to the standard catalogue."
                ) % {"name": medicine.name, "code": medicine.code})
                return redirect("medicine:medicine_detail", pk=medicine.pk)
        return render(request, "catalogue/register.html",
                      {"product": product, "form": form})


class CatalogueProductCreateView(PlatformStaffRequiredMixin, CreateView):
    """Adds a product the catalogue does not have.

    Recorded with `data_source = LOCAL` so reports can distinguish
    locally-added entries from authority-sourced ones. Platform-only: a
    pharmacy that genuinely can't find something in the catalogue should
    ask platform staff to add it, rather than every company growing its
    own divergent copy of shared reference data.
    """

    model = CatalogueProduct
    form_class = CatalogueProductForm
    template_name = "catalogue/product_form.html"
    success_url = reverse_lazy("catalogue:product_list")

    def form_valid(self, form):
        from .models import DataSource

        form.instance.data_source = DataSource.LOCAL
        messages.success(self.request, _(
            "Added to the catalogue as a local entry. If this product is on the "
            "EFDA register, add its registration number so it can be verified."
        ))
        return super().form_valid(form)
