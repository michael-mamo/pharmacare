from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView
"""
Inventory views: an overview dashboard, the stock-movement recording form,
a movement history list, and the Low Stock / Out of Stock reports.

Access differs by role (see apps.accounts.models.User):
  - can_view_inventory_reports: Administrator, Store Manager, Pharmacist —
    everyone who needs to know what's low or out, to dispense or reorder.
    Cashier is blocked (403); stock reporting isn't part of their job.
  - can_manage_stock_movements: Administrator, Store Manager only — the
    same roles that can already adjust the catalog and record purchases.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import F
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

from django.views.generic import ListView, TemplateView

from apps.accounts.permissions import RoleRequiredMixin
from apps.medicine.models import Medicine

from .forms import StockMovementForm
from .models import StockMovement
from .services import apply_stock_movement

REPORT_ROLES = ["STORE_MANAGER", "PHARMACIST"]  # Administrator always passes
MANAGE_ROLES = ["STORE_MANAGER"]


class InventoryOverviewView(RoleRequiredMixin, ListView):
    """Stock health KPIs plus the actual current-stock list.

    This is a ListView rather than a TemplateView so the medicine list can be
    searched, filtered and paginated — the earlier version showed only KPI
    cards and recent movements, which meant the page never actually told you
    what was in stock.
    """

    model = Medicine
    template_name = "inventory/overview.html"
    context_object_name = "medicines"
    paginate_by = 15
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        qs = Medicine.objects.filter(is_active=True).select_related("category", "supplier")
        query = self.request.GET.get("q")
        stock_filter = self.request.GET.get("stock")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(code__icontains=query)
        if stock_filter == "low":
            qs = qs.filter(quantity__lte=F("reorder_level"), quantity__gt=0)
        elif stock_filter == "out":
            qs = qs.filter(quantity=0)
        elif stock_filter == "expired":
            qs = qs.filter(expiry_date__lt=timezone.localdate())
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        medicines = Medicine.objects.filter(is_active=True)
        context["low_stock_count"] = medicines.filter(quantity__lte=F("reorder_level"), quantity__gt=0).count()
        context["out_of_stock_count"] = medicines.filter(quantity=0).count()
        context["expired_count"] = medicines.filter(expiry_date__lt=timezone.localdate()).count()
        context["total_stock_units"] = sum(medicines.values_list("quantity", flat=True))
        context["recent_movements"] = StockMovement.objects.select_related("medicine", "performed_by")[:8]
        context["can_manage"] = self.request.user.can_manage_stock_movements()
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["stock_filter"] = self.request.GET.get("stock", "")
        return context


class StockMovementListView(RoleRequiredMixin, ListView):
    model = StockMovement
    template_name = "inventory/movement_list.html"
    context_object_name = "movements"
    paginate_by = 25
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        qs = StockMovement.objects.select_related("medicine", "performed_by")
        movement_type = self.request.GET.get("type")
        query = self.request.GET.get("q")
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        if query:
            qs = qs.filter(medicine__name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = self.request.user.can_manage_stock_movements()
        return context


class LowStockReportView(RoleRequiredMixin, ListView):
    template_name = "inventory/low_stock_report.html"
    context_object_name = "medicines"
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        return Medicine.objects.filter(
            is_active=True, quantity__lte=F("reorder_level"), quantity__gt=0
        ).select_related("category", "supplier").order_by("quantity")


class ExpiredStockReportView(RoleRequiredMixin, ListView):
    """Expired and soon-to-expire stock. Added so the "Expired Medicines" KPI
    card can navigate somewhere, matching the Low Stock and Out of Stock
    cards — previously it was the only unclickable figure on the page."""

    template_name = "inventory/expired_report.html"
    context_object_name = "medicines"
    paginate_by = 25
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        today = timezone.localdate()
        window = self.request.GET.get("window", "expired")
        qs = Medicine.objects.filter(is_active=True).select_related("category", "supplier")
        if window == "30":
            qs = qs.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))
        elif window == "60":
            qs = qs.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=60))
        else:
            qs = qs.filter(expiry_date__lt=today)
        return qs.order_by("expiry_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        active = Medicine.objects.filter(is_active=True)
        context["window"] = self.request.GET.get("window", "expired")
        context["expired_count"] = active.filter(expiry_date__lt=today).count()
        context["expiring_30"] = active.filter(
            expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30)).count()
        context["expiring_60"] = active.filter(
            expiry_date__gte=today, expiry_date__lte=today + timedelta(days=60)).count()
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["today"] = today
        return context


class OutOfStockReportView(RoleRequiredMixin, ListView):
    template_name = "inventory/out_of_stock_report.html"
    context_object_name = "medicines"
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        return Medicine.objects.filter(is_active=True, quantity=0).select_related("category", "supplier")


class BatchListView(RoleRequiredMixin, ListView):
    """Per-batch stock with its own unit cost.

    This is where the batch costing becomes visible: when a medicine has been
    bought at two different prices, you can see both batches, what each cost,
    and which will be dispensed first (FEFO — soonest expiry first).
    Cost columns are hidden from roles not cleared for cost data.
    """

    template_name = "inventory/batch_list.html"
    context_object_name = "batches"
    paginate_by = 30
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        from .batches import StockBatch

        qs = StockBatch.objects.select_related("medicine", "purchase_item__purchase")
        query = self.request.GET.get("q")
        show = self.request.GET.get("show", "available")
        if query:
            qs = qs.filter(medicine__name__icontains=query) | qs.filter(batch_number__icontains=query)
        if show == "available":
            qs = qs.filter(quantity_remaining__gt=0)
        elif show == "depleted":
            qs = qs.filter(quantity_remaining=0)
        return qs.order_by("medicine__name", "expiry_date", "received_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["show"] = self.request.GET.get("show", "available")
        return context


class StockMovementCreateView(RoleRequiredMixin, TemplateView):
    """Manual GET/POST handling instead of Django's generic FormView: the
    actual state change goes through apps.inventory.services.apply_stock_movement
    (which validates business rules like "can't remove more than is in
    stock") rather than a plain ModelForm.save()."""

    template_name = "inventory/movement_form.html"
    allowed_roles = MANAGE_ROLES

    def get(self, request, *args, **kwargs):
        return self.render_to_response({"form": StockMovementForm()})

    def post(self, request, *args, **kwargs):
        form = StockMovementForm(request.POST)
        if form.is_valid():
            try:
                apply_stock_movement(
                    medicine_id=form.cleaned_data["medicine"].pk,
                    movement_type=form.cleaned_data["movement_type"],
                    quantity=form.cleaned_data["quantity"],
                    destination=form.cleaned_data["destination"],
                    reason=form.cleaned_data["reason"],
                    user=request.user,
                )
            except ValidationError as e:
                form.add_error(None, e.message if hasattr(e, "message") else str(e))
                return self.render_to_response({"form": form})
            messages.success(request, "Stock movement recorded.")
            return redirect("inventory:movement_list")
        return self.render_to_response({"form": form})


# ===========================================================================
# Full inventory management: ledger, stocktake, reorder planning, aging
# ===========================================================================
class StockLedgerView(RoleRequiredMixin, ListView):
    """The complete history of why stock is what it is.

    Every cause appears here — purchases, sales, voids, transfers, manual
    movements and stocktakes — with a running balance, which is what makes it
    possible to answer "where did those 40 units go?" without cross-checking
    four different screens.
    """

    template_name = "inventory/ledger.html"
    context_object_name = "entries"
    paginate_by = 50
    allowed_roles = REPORT_ROLES

    def get_queryset(self):
        from apps.branches.context import branch_scope

        from .stocktake import StockLedger

        qs = StockLedger.objects.select_related(
            "medicine", "branch", "performed_by"
        )
        qs = branch_scope(qs, self.request)
        query = self.request.GET.get("q")
        source = self.request.GET.get("source")
        medicine = self.request.GET.get("medicine")
        if query:
            qs = qs.filter(medicine__name__icontains=query) | qs.filter(
                reference__icontains=query
            )
        if source:
            qs = qs.filter(source=source)
        if medicine:
            qs = qs.filter(medicine_id=medicine)
        return qs

    def get_context_data(self, **kwargs):
        from .stocktake import LedgerSource

        context = super().get_context_data(**kwargs)
        context["sources"] = LedgerSource.choices
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["selected_source"] = self.request.GET.get("source", "")
        return context


class StockTakeListView(RoleRequiredMixin, ListView):
    template_name = "inventory/stocktake_list.html"
    context_object_name = "stocktakes"
    paginate_by = 20
    allowed_roles = MANAGE_ROLES

    def get_queryset(self):
        from apps.branches.context import branch_scope

        from .stocktake import StockTake

        qs = StockTake.objects.select_related("branch", "started_by", "posted_by")
        return branch_scope(qs, self.request)

    def get_context_data(self, **kwargs):
        from .forms import StockTakeStartForm
        from .stocktake import StockTake, StockTakeStatus

        context = super().get_context_data(**kwargs)
        context["form"] = StockTakeStartForm()
        branch = getattr(self.request, "branch", None)
        context["open_stocktake"] = (
            StockTake.objects.filter(branch=branch, status=StockTakeStatus.DRAFT).first()
            if branch else None
        )
        return context


class StockTakeStartView(RoleRequiredMixin, View):
    allowed_roles = MANAGE_ROLES

    def post(self, request):
        from .forms import StockTakeStartForm
        from .stocktake_services import open_stocktake

        form = StockTakeStartForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("Could not start the stocktake."))
            return redirect("inventory:stocktake_list")
        try:
            stocktake = open_stocktake(
                branch=getattr(request, "branch", None),
                category=form.cleaned_data.get("category"),
                user=request.user,
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect("inventory:stocktake_list")
        messages.success(request, _(
            "%(ref)s opened with %(n)s products to count."
        ) % {"ref": stocktake.reference, "n": stocktake.total_lines})
        return redirect("inventory:stocktake_detail", pk=stocktake.pk)


class StockTakeDetailView(RoleRequiredMixin, DetailView):
    template_name = "inventory/stocktake_detail.html"
    context_object_name = "stocktake"
    allowed_roles = MANAGE_ROLES

    def get_queryset(self):
        from .stocktake import StockTake

        return StockTake.objects.select_related("branch", "started_by", "posted_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lines = self.object.lines.select_related("medicine", "medicine__category")
        show = self.request.GET.get("show", "all")
        if show == "uncounted":
            lines = lines.filter(counted_quantity__isnull=True)
        elif show == "variance":
            lines = [l for l in lines if l.has_variance]
        elif show == "counted":
            lines = lines.filter(counted_quantity__isnull=False)
        context["lines"] = lines
        context["show"] = show
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        return context


class StockTakeSaveCountsView(RoleRequiredMixin, View):
    """Saves counted figures without posting them.

    Counting is saved separately from posting on purpose: a large count runs
    over hours or shifts, and nobody should have to finish it in one sitting
    or risk losing their work.
    """

    allowed_roles = MANAGE_ROLES

    def post(self, request, pk):
        from .stocktake import StockTake

        stocktake = get_object_or_404(StockTake, pk=pk)
        if not stocktake.is_editable:
            messages.error(request, _("This stocktake is closed."))
            return redirect("inventory:stocktake_detail", pk=pk)

        saved = 0
        for line in stocktake.lines.all():
            raw = request.POST.get(f"count_{line.pk}")
            note = request.POST.get(f"note_{line.pk}", "")
            if raw is None:
                continue
            raw = raw.strip()
            if raw == "":
                # Blank clears a count rather than meaning zero — an
                # uncounted line must stay uncounted so posting skips it.
                if line.counted_quantity is not None:
                    line.counted_quantity = None
                    line.counted_at = None
                    line.note = note
                    line.save(update_fields=["counted_quantity", "counted_at", "note"])
                continue
            try:
                value = int(raw)
            except ValueError:
                continue
            if value < 0:
                continue
            line.counted_quantity = value
            line.counted_at = timezone.now()
            line.note = note
            line.save(update_fields=["counted_quantity", "counted_at", "note"])
            saved += 1

        messages.success(request, _("%(n)s counts saved.") % {"n": saved})
        return redirect(f"{reverse('inventory:stocktake_detail', kwargs={'pk': pk})}"
                        f"?show={request.POST.get('show', 'all')}")


class StockTakePostView(RoleRequiredMixin, View):
    allowed_roles = MANAGE_ROLES

    def post(self, request, pk):
        from .stocktake import StockTake
        from .stocktake_services import post_stocktake

        stocktake = get_object_or_404(StockTake, pk=pk)
        try:
            result = post_stocktake(stocktake=stocktake, user=request.user)
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect("inventory:stocktake_detail", pk=pk)
        messages.success(request, _(
            "%(ref)s posted: %(adj)s adjustment(s), net %(net)s units, value %(val)s. "
            "%(un)s product(s) were not counted and were left untouched."
        ) % {"ref": stocktake.reference, "adj": result["adjustments"],
             "net": result["net_units"], "val": result["value"],
             "un": result["lines_uncounted"]})
        return redirect("inventory:stocktake_detail", pk=pk)


class StockTakeCancelView(RoleRequiredMixin, View):
    allowed_roles = MANAGE_ROLES

    def post(self, request, pk):
        from .stocktake import StockTake
        from .stocktake_services import cancel_stocktake

        stocktake = get_object_or_404(StockTake, pk=pk)
        try:
            cancel_stocktake(stocktake=stocktake, user=request.user)
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
        else:
            messages.success(request, _("Stocktake cancelled. No stock was changed."))
        return redirect("inventory:stocktake_list")


class ReorderPlanView(RoleRequiredMixin, TemplateView):
    """What to order and how much, based on actual consumption."""

    template_name = "inventory/reorder_plan.html"
    allowed_roles = MANAGE_ROLES

    def get_context_data(self, **kwargs):
        from .stocktake_services import (
            TARGET_DAYS_OF_COVER, VELOCITY_WINDOW_DAYS, reorder_suggestions,
        )

        context = super().get_context_data(**kwargs)
        branch = getattr(self.request, "branch", None)
        include_healthy = self.request.GET.get("all") == "1"
        try:
            target = int(self.request.GET.get("days") or TARGET_DAYS_OF_COVER)
        except ValueError:
            target = TARGET_DAYS_OF_COVER
        target = max(7, min(target, 365))

        suggestions = reorder_suggestions(
            branch=branch, target_days=target, include_healthy=include_healthy
        )
        context["suggestions"] = suggestions
        context["target_days"] = target
        context["window_days"] = VELOCITY_WINDOW_DAYS
        context["include_healthy"] = include_healthy
        context["total_cost"] = sum((s["estimated_cost"] for s in suggestions), Decimal("0.00"))
        context["out_of_stock"] = sum(1 for s in suggestions if s["is_out"])
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        # Group by supplier: an order is placed with a supplier, not with a
        # spreadsheet, so this is the shape the user actually needs.
        by_supplier = {}
        for s in suggestions:
            key = s["supplier"].name if s["supplier"] else str(_("No supplier set"))
            by_supplier.setdefault(key, []).append(s)
        context["by_supplier"] = sorted(by_supplier.items())
        return context


class StockAgingView(RoleRequiredMixin, TemplateView):
    """Stock value bucketed by remaining shelf life."""

    template_name = "inventory/aging.html"
    allowed_roles = REPORT_ROLES

    def get_context_data(self, **kwargs):
        from .stocktake_services import stock_aging

        context = super().get_context_data(**kwargs)
        branch = getattr(self.request, "branch", None)
        buckets = stock_aging(branch=branch)
        context["buckets"] = buckets
        context["total_units"] = sum(b["units"] for b in buckets)
        context["total_value"] = sum((b["value"] for b in buckets), Decimal("0.00"))
        at_risk = [b for b in buckets if str(b["label"]) in ("Expired", "0–30 days")]
        context["at_risk_value"] = sum((b["value"] for b in at_risk), Decimal("0.00"))
        context["can_view_cost"] = self.request.user.can_view_cost_price()
        context["branch"] = branch
        return context
