"""
Branch views.

Managing branches is an Administrator task. The branch *switcher* is
available to anyone who can see more than one branch (in practice,
Administrators), and the stock view is open to the roles that already have
inventory access.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import AdministratorRequiredMixin, RoleRequiredMixin
from apps.branches.context import SESSION_KEY
from apps.medicine.models import Medicine

from .forms import BranchForm, TransferForm
from .models import Branch, BranchStock

STOCK_ROLES = ["STORE_MANAGER", "PHARMACIST"]
TRANSFER_ROLES = ["STORE_MANAGER"]


class BranchListView(AdministratorRequiredMixin, ListView):
    model = Branch
    template_name = "branches/branch_list.html"
    context_object_name = "branches"

    def get_queryset(self):
        return Branch.objects.select_related("manager").prefetch_related("stock_levels")


class BranchDetailView(AdministratorRequiredMixin, DetailView):
    model = Branch
    template_name = "branches/branch_detail.html"
    context_object_name = "branch"

    def get_context_data(self, **kwargs):
        from apps.sales.models import Sale, SaleStatus

        context = super().get_context_data(**kwargs)
        branch = self.object
        context["staff"] = branch.staff.filter(is_active=True).order_by("role", "username")
        context["low_stock"] = (
            branch.stock_levels.select_related("medicine")
            .filter(quantity__gt=0, quantity__lte=F("reorder_level"))
            .order_by("quantity")[:10]
        )
        context["out_of_stock"] = (
            branch.stock_levels.select_related("medicine").filter(quantity=0).count()
        )
        sales = Sale.objects.filter(branch=branch, status=SaleStatus.COMPLETED)
        context["sale_count"] = sales.count()
        context["recent_sales"] = sales.select_related("customer").prefetch_related("items")[:8]
        context["purchase_count"] = branch.purchase_invoices.count()
        return context


class BranchCreateView(AdministratorRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = "branches/branch_form.html"
    success_url = reverse_lazy("branches:branch_list")

    def dispatch(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is not None and org.is_over_branch_limit:
            messages.error(request, _(
                "You've reached your plan's branch limit (%(limit)s). Contact "
                "your platform administrator to raise it."
            ) % {"limit": org.max_branches})
            return redirect("branches:branch_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _("Branch created. Assign staff to it next, and "
                                         "stock it with a purchase or a transfer."))
        return super().form_valid(form)


class BranchUpdateView(AdministratorRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = "branches/branch_form.html"
    success_url = reverse_lazy("branches:branch_list")

    def form_valid(self, form):
        messages.success(self.request, _("Branch updated."))
        return super().form_valid(form)


class SwitchBranchView(LoginRequiredMixin, View):
    """Changes the Administrator's active branch for this session.

    Validated server-side: a user who is not allowed a branch cannot select
    it by posting its id, and a branch-assigned user cannot switch at all.
    """

    def post(self, request):
        branch_id = request.POST.get("branch")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

        if not request.user.can_access_all_branches():
            messages.error(request, _("Your account is fixed to a single branch."))
            return redirect(next_url)

        branch = Branch.objects.filter(pk=branch_id, is_active=True).first()
        if branch is None or not request.user.may_use_branch(branch):
            messages.error(request, _("That branch is not available."))
            return redirect(next_url)

        request.session[SESSION_KEY] = branch.pk
        messages.success(request, _("Now working in %(branch)s.") % {"branch": branch.name})
        return redirect(next_url)


class BranchStockListView(RoleRequiredMixin, ListView):
    """Stock for the active branch, or a chosen branch for Administrators."""

    template_name = "branches/branch_stock.html"
    context_object_name = "stock_rows"
    paginate_by = 25
    allowed_roles = STOCK_ROLES

    def get_branch(self):
        requested = self.request.GET.get("branch")
        if requested and self.request.user.can_access_all_branches():
            branch = Branch.objects.filter(pk=requested, is_active=True).first()
            if branch:
                return branch
        return getattr(self.request, "branch", None)

    def get_queryset(self):
        branch = self.get_branch()
        if branch is None:
            return BranchStock.objects.none()
        qs = BranchStock.objects.filter(branch=branch).select_related(
            "medicine", "medicine__category"
        )
        query = self.request.GET.get("q")
        level = self.request.GET.get("level")
        if query:
            qs = qs.filter(medicine__name__icontains=query) | qs.filter(
                medicine__code__icontains=query, branch=branch
            )
        if level == "low":
            qs = qs.filter(quantity__gt=0, quantity__lte=F("reorder_level"))
        elif level == "out":
            qs = qs.filter(quantity=0)
        return qs.order_by("medicine__name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branch = self.get_branch()
        context["branch"] = branch
        context["branches"] = self.request.user.accessible_branches()
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["can_transfer"] = (
            self.request.user.is_administrator or self.request.user.is_store_manager
        )
        context["level"] = self.request.GET.get("level", "")
        if branch:
            context["totals"] = {
                "units": branch.total_stock_units,
                "low": branch.low_stock_count,
                "out": branch.out_of_stock_count,
                "products": branch.product_count,
            }
        return context


class BranchComparisonView(AdministratorRequiredMixin, ListView):
    """Side-by-side stock across every branch — the view that only makes
    sense with more than one branch, and the reason to have this page."""

    template_name = "branches/comparison.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = Medicine.objects.filter(is_active=True).prefetch_related(
            "branch_stocks__branch"
        )
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(name__icontains=query)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = list(Branch.objects.filter(is_active=True).order_by("-is_main", "name"))
        context["branches"] = branches
        table = []
        for medicine in context["rows"]:
            by_branch = {bs.branch_id: bs for bs in medicine.branch_stocks.all()}
            cells = []
            for branch in branches:
                row = by_branch.get(branch.pk)
                cells.append({
                    "branch": branch,
                    "quantity": row.quantity if row else 0,
                    "is_low": row.is_low_stock if row else False,
                    "is_out": (row.quantity == 0) if row else True,
                })
            table.append({"medicine": medicine, "cells": cells,
                          "total": sum(c["quantity"] for c in cells)})
        context["table"] = table
        return context


class TransferCreateView(RoleRequiredMixin, View):
    """Moves stock from the active branch to another branch."""

    allowed_roles = TRANSFER_ROLES

    def get(self, request):
        form = TransferForm(source_branch=getattr(request, "branch", None))
        return render(request, "branches/transfer_form.html",
                      {"form": form, "source_branch": request.branch})

    def post(self, request):
        branch = getattr(request, "branch", None)
        form = TransferForm(request.POST, source_branch=branch)
        if form.is_valid():
            from apps.inventory.models import MovementType
            from apps.inventory.services import apply_stock_movement

            try:
                movement = apply_stock_movement(
                    medicine_id=form.cleaned_data["medicine"].pk,
                    movement_type=MovementType.TRANSFER,
                    quantity=form.cleaned_data["quantity"],
                    branch=branch,
                    destination_branch=form.cleaned_data["destination_branch"],
                    reason=form.cleaned_data.get("reason", ""),
                    user=request.user,
                )
            except ValidationError as e:
                for message in e.messages:
                    form.add_error(None, message)
            else:
                messages.success(request, _(
                    "Transferred %(qty)s × %(name)s to %(dest)s."
                ) % {"qty": movement.quantity, "name": movement.medicine.name,
                     "dest": form.cleaned_data["destination_branch"].name})
                return redirect("branches:stock")
        return render(request, "branches/transfer_form.html",
                      {"form": form, "source_branch": branch})
