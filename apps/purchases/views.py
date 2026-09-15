"""
Purchase invoice views.

Recording a purchase uses a function-based view rather than a CBV: the
header form + line-item formset combination is the one case in this
project where Django's idiomatic pattern is a plain function view (CBVs
don't compose cleanly with inline formsets without a lot of boilerplate).
Every other view in this app is a standard CBV.
"""
import logging

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.generic import DeleteView, DetailView, ListView

from apps.accounts.permissions import RoleRequiredMixin, role_required

from .forms import PurchaseInvoiceForm, PurchaseItemFormSet
from .models import PurchaseInvoice

logger = logging.getLogger(__name__)

VIEW_ROLES = ["STORE_MANAGER"]  # Administrator always passes via RoleRequiredMixin
MANAGE_ROLES = ["STORE_MANAGER"]
DELETE_ROLES = []  # Administrator only — see User.can_delete_purchases


class PurchaseListView(RoleRequiredMixin, ListView):
    model = PurchaseInvoice
    template_name = "purchases/purchase_list.html"
    context_object_name = "purchases"
    paginate_by = 20
    allowed_roles = VIEW_ROLES

    def get_queryset(self):
        qs = PurchaseInvoice.objects.select_related("supplier").prefetch_related("items")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(purchase_number__icontains=query) | qs.filter(supplier__name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.can_delete_purchases()
        return context


class PurchaseDetailView(RoleRequiredMixin, DetailView):
    model = PurchaseInvoice
    template_name = "purchases/purchase_detail.html"
    context_object_name = "purchase"
    allowed_roles = VIEW_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = self.request.user.can_delete_purchases()
        return context


class PurchaseDeleteView(RoleRequiredMixin, DeleteView):
    model = PurchaseInvoice
    template_name = "purchases/purchase_confirm_delete.html"
    success_url = "/purchases/"
    allowed_roles = DELETE_ROLES  # empty list + Administrator bypass = Administrator only

    def form_valid(self, form):
        # PurchaseItem.delete() reverses the stock effect per line (see
        # models.py) — iterate explicitly rather than relying on CASCADE's
        # bulk delete, which would skip each item's overridden delete().
        for item in self.object.items.all():
            item.delete()
        messages.success(
            self.request,
            f"Purchase {self.object.purchase_number} deleted and its stock effect reversed.",
        )
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


@role_required("STORE_MANAGER")
def purchase_create(request):
    """Record a new purchase invoice: header + one or more line items.
    Each line item increases the corresponding medicine's stock on save
    (see PurchaseItem.save()) — all inside one DB transaction so a bad
    line can't leave stock partially updated."""
    if request.method == "POST":
        invoice_form = PurchaseInvoiceForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)
        if invoice_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = invoice_form.save(commit=False)
                invoice.branch = getattr(request, "branch", None)
                invoice.recorded_by = request.user
                invoice.save()
                formset.instance = invoice
                formset.save()
            # Notify managers that stock moved (Phase 6). Kept outside the
            # transaction-critical path: a notification failure must never
            # roll back a recorded purchase.
            try:
                from apps.notifications.services import notify_new_purchase

                notify_new_purchase(invoice)
            except Exception:
                logger.exception("Could not create new-purchase notification")
            messages.success(request, f"Purchase {invoice.purchase_number} recorded — stock updated.")
            return redirect("purchases:purchase_detail", pk=invoice.pk)
    else:
        invoice_form = PurchaseInvoiceForm()
        formset = PurchaseItemFormSet()

    return render(
        request,
        "purchases/purchase_form.html",
        {"invoice_form": invoice_form, "formset": formset},
    )
