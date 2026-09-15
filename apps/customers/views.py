"""
Customer views. Unlike Suppliers, every operational role deals with
customers day to day (registering a walk-in, updating contact info at the
counter), so view/create/edit are open to all authenticated staff.
Deleting a customer record is still an Administrator/Store Manager action.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import RoleRequiredMixin

from .forms import CustomerForm
from .models import Customer

DELETE_ROLES = ["STORE_MANAGER"]  # Administrator always passes


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.all()
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(phone__icontains=query) | qs.filter(email__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.can_delete_customers()
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.can_delete_customers()
        return context


class CustomerFormMixin:
    """Shared by Create/Update so the form always knows which user is
    filling it in (controls whether the loyalty_points field is shown)."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CustomerCreateView(LoginRequiredMixin, CustomerFormMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "Customer registered successfully.")
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, CustomerFormMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "Customer updated successfully.")
        return super().form_valid(form)


class CustomerDeleteView(RoleRequiredMixin, DeleteView):
    model = Customer
    template_name = "customers/customer_confirm_delete.html"
    success_url = reverse_lazy("customers:customer_list")
    allowed_roles = DELETE_ROLES

    def form_valid(self, form):
        messages.success(self.request, "Customer deleted.")
        return super().form_valid(form)
