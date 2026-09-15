"""
Medicine catalog views.

Access differs by role and by action, not just by page:
  - View (list/detail): every authenticated role, including Cashier — they
    need to look up a medicine at the till.
  - Cost price: hidden from the list/detail templates for Pharmacist and
    Cashier (see User.can_view_cost_price); Selling price is always shown.
  - Create/Edit/Delete: Administrator and Store Manager only.
Category follows the same manage/view split.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import RoleRequiredMixin

from .barcodes import generate_barcode_svg, generate_qr_data_uri
from .forms import CategoryForm, MedicineForm
from .models import Category, Medicine, ProductType

MANAGE_ROLES = ["STORE_MANAGER"]  # Administrator always passes via RoleRequiredMixin


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "medicine/category_list.html"
    context_object_name = "categories"
    paginate_by = 20

    def get_queryset(self):
        qs = Category.objects.all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = self.request.user.can_manage_catalog()
        return context


class CategoryCreateView(RoleRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "medicine/category_form.html"
    success_url = reverse_lazy("medicine:category_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully.")
        return super().form_valid(form)


class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "medicine/category_form.html"
    success_url = reverse_lazy("medicine:category_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully.")
        return super().form_valid(form)


class CategoryDeleteView(RoleRequiredMixin, DeleteView):
    model = Category
    template_name = "medicine/category_confirm_delete.html"
    success_url = reverse_lazy("medicine:category_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "This category cannot be deleted while medicines are still assigned to it. "
                "Move or delete those medicines first.",
            )
            return self.render_to_response(self.get_context_data())
        messages.success(self.request, "Category deleted.")
        return response


# ---------------------------------------------------------------------------
# Medicine
# ---------------------------------------------------------------------------
class MedicineListView(LoginRequiredMixin, ListView):
    model = Medicine
    template_name = "medicine/medicine_list.html"
    context_object_name = "medicines"
    paginate_by = 20

    def get_queryset(self):
        qs = Medicine.objects.select_related("category", "supplier")
        query = self.request.GET.get("q")
        category_id = self.request.GET.get("category")
        product_type = self.request.GET.get("type")
        stock_filter = self.request.GET.get("stock")

        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(code__icontains=query) | \
                 qs.filter(generic_name__icontains=query) | qs.filter(barcode__icontains=query)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if product_type:
            qs = qs.filter(product_type=product_type)
        if stock_filter == "low":
            qs = qs.filter(quantity__lte=F("reorder_level"))
        elif stock_filter == "out":
            qs = qs.filter(quantity=0)
        elif stock_filter == "expired":
            qs = qs.filter(expiry_date__lt=timezone.localdate())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["product_types"] = ProductType.choices
        context["can_manage"] = self.request.user.can_manage_catalog()
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        return context


class MedicineDetailView(LoginRequiredMixin, DetailView):
    model = Medicine
    template_name = "medicine/medicine_detail.html"
    context_object_name = "medicine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = self.request.user.can_manage_catalog()
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        return context


class MedicineFormMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class MedicineCreateView(RoleRequiredMixin, MedicineFormMixin, CreateView):
    model = Medicine
    form_class = MedicineForm
    template_name = "medicine/medicine_form.html"
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.object.is_standardized:
            messages.warning(self.request, (
                f'"{self.object.name}" was added without a standard catalogue link. '
                "It's saved and usable, but flagged as Not Standardised — its "
                "identity won't roll up with the same medicine at other pharmacies "
                "in group reporting. Edit it later to link a catalogue entry if "
                "one turns out to exist."
            ))
        else:
            messages.success(self.request, "Medicine added successfully.")
        return response


class MedicineUpdateView(RoleRequiredMixin, MedicineFormMixin, UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = "medicine/medicine_form.html"
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.object.is_standardized:
            messages.warning(self.request, (
                f'"{self.object.name}" is saved but still Not Standardised — no '
                "catalogue link. Link one if it turns out to exist."
            ))
        else:
            messages.success(self.request, "Medicine updated successfully.")
        return response


class MedicineDeleteView(RoleRequiredMixin, DeleteView):
    model = Medicine
    template_name = "medicine/medicine_confirm_delete.html"
    success_url = reverse_lazy("medicine:medicine_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Medicine deleted.")
        return super().form_valid(form)


class MedicineLabelView(LoginRequiredMixin, DetailView):
    """Printable shelf label: barcode + QR + key facts. Available to every
    role that can view the catalog (Cashiers included — they may need to
    reprint a torn label at the till)."""

    model = Medicine
    template_name = "medicine/medicine_label.html"
    context_object_name = "medicine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        medicine = self.object
        barcode_value = medicine.barcode or medicine.code
        context["barcode_svg"] = generate_barcode_svg(barcode_value)
        context["qr_data_uri"] = generate_qr_data_uri(
            self.request.build_absolute_uri(medicine.get_absolute_url())
        )
        return context
