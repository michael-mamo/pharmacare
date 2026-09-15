"""
Supplier views. Access is intentionally asymmetric by role:
  - View (list/detail): Administrator, Store Manager, Pharmacist.
    Cashiers have no need to see supplier/business data and are blocked
    (403), unlike Medicines/Categories which every role can browse.
  - Create/Edit/Delete: Administrator and Store Manager only.
See apps.accounts.models.User.can_view_suppliers / can_manage_suppliers,
which this module mirrors via RoleRequiredMixin.allowed_roles.
"""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import RoleRequiredMixin

from .forms import SupplierForm
from .models import Supplier

VIEW_ROLES = ["STORE_MANAGER", "PHARMACIST"]  # Administrator always passes (see RoleRequiredMixin)
MANAGE_ROLES = ["STORE_MANAGER"]


class SupplierListView(RoleRequiredMixin, ListView):
    model = Supplier
    template_name = "suppliers/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 20
    allowed_roles = VIEW_ROLES

    def get_queryset(self):
        qs = Supplier.objects.all()
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(contact_person__icontains=query) | qs.filter(phone__icontains=query)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = self.request.user.can_manage_suppliers()
        return context


class SupplierDetailView(RoleRequiredMixin, DetailView):
    model = Supplier
    template_name = "suppliers/supplier_detail.html"
    context_object_name = "supplier"
    allowed_roles = VIEW_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = self.request.user.can_manage_suppliers()
        return context


class SupplierCreateView(RoleRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_form.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Supplier added successfully.")
        return super().form_valid(form)


class SupplierUpdateView(RoleRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_form.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Supplier updated successfully.")
        return super().form_valid(form)


class SupplierDeleteView(RoleRequiredMixin, DeleteView):
    model = Supplier
    template_name = "suppliers/supplier_confirm_delete.html"
    success_url = reverse_lazy("suppliers:supplier_list")
    allowed_roles = MANAGE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Supplier deleted.")
        return super().form_valid(form)
