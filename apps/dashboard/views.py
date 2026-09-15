"""
Main dashboard view.

KPI cards and charts are computed from live querysets against whichever
domain apps are currently installed. Phase 1 ships with only `accounts`
and `dashboard` installed, so medicine/sales/purchase figures correctly
report as zero rather than raising ImportError — each block below is
guarded so the dashboard degrades gracefully and then "lights up" with
real numbers the moment Phase 2/3/4 apps are added to INSTALLED_APPS,
with no changes needed here beyond uncommenting the noted query.

This keeps the dashboard "complete" at every phase instead of shipping
a broken import that gets patched later.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone
from django.views.generic import RedirectView, TemplateView

from apps.accounts.permissions import AdministratorRequiredMixin


class RoleLandingView(LoginRequiredMixin, RedirectView):
    """Sends each user to the first page that's actually useful to them.

    The dashboard is Administrator-only (it aggregates cost prices, profit,
    and company-wide figures), so every other role needs its own landing
    page — otherwise logging in would dump them straight onto a 403.
    Used for both LOGIN_REDIRECT_URL and the site root.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_administrator:
            return reverse("dashboard:home")
        if user.can_operate_pos():          # Cashier, Pharmacist
            return reverse("sales:pos")
        if user.can_view_inventory_reports():  # Store Manager
            return reverse("inventory:overview")
        return reverse("accounts:profile")   # safe fallback for any new role


class DashboardHomeView(AdministratorRequiredMixin, TemplateView):
    """Administrator-only. Surfaces cost prices, profit margins, and
    company-wide performance, so it is deliberately not shared with
    Cashier / Pharmacist / Store Manager — each of whom has their own
    role-appropriate landing page (see RoleLandingView)."""

    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)

        # The Administrator dashboard follows the branch selected in the
        # navbar, so switching branch re-reads every figure on the page.
        branch = getattr(self.request, "branch", None)
        context.update(self._medicine_kpis(branch))
        context.update(self._people_kpis())
        context.update(self._sales_kpis(today, month_start, branch))
        context.update(self._purchase_kpis(branch))
        context["chart_data"] = json.dumps(self._chart_data(branch))
        context["today"] = today
        context["active_branch"] = branch
        context["branch_count"] = self._branch_count()
        return context

    @staticmethod
    def _branch_count():
        try:
            from apps.branches.models import Branch

            return Branch.objects.filter(is_active=True).count()
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Each helper checks whether the models it needs exist yet (they are
    # introduced in later phases) using django.apps.apps.is_installed /
    # get_model, so Phase 1 runs cleanly with all figures at zero.
    # ------------------------------------------------------------------
    def _medicine_kpis(self, branch=None):
        data = {"total_medicines": 0, "total_categories": 0, "low_stock_count": 0, "expired_count": 0}
        if django_apps.is_installed("apps.medicine"):
            Medicine = django_apps.get_model("medicine", "Medicine")
            Category = django_apps.get_model("medicine", "Category")
            data["total_categories"] = Category.objects.count()
            if branch is not None:
                # Per branch: count what this branch actually stocks, and
                # compare against ITS reorder levels.
                from apps.branches.models import BranchStock

                rows = BranchStock.objects.filter(branch=branch, medicine__is_active=True)
                data["total_medicines"] = rows.count()
                data["low_stock_count"] = rows.filter(
                    quantity__lte=F("reorder_level")
                ).count()
                data["expired_count"] = rows.filter(
                    quantity__gt=0, medicine__expiry_date__lt=timezone.localdate()
                ).count()
            else:
                data["total_medicines"] = Medicine.objects.count()
                data["low_stock_count"] = Medicine.objects.filter(
                    quantity__lte=F("reorder_level")
                ).count()
                data["expired_count"] = Medicine.objects.filter(
                    expiry_date__lt=timezone.localdate()
                ).count()
        return data

    def _people_kpis(self):
        data = {"total_customers": 0, "total_suppliers": 0}
        if django_apps.is_installed("apps.customers"):
            Customer = django_apps.get_model("customers", "Customer")
            data["total_customers"] = Customer.objects.count()
        if django_apps.is_installed("apps.suppliers"):
            Supplier = django_apps.get_model("suppliers", "Supplier")
            data["total_suppliers"] = Supplier.objects.count()
        return data

    def _sales_kpis(self, today, month_start, branch=None):
        data = {"todays_sales": 0, "monthly_sales": 0, "sales_value": 0, "profit_summary": 0}
        if django_apps.is_installed("apps.sales"):
            Sale = django_apps.get_model("sales", "Sale")
            completed = Sale.objects.filter(status="COMPLETED").prefetch_related("items__medicine")
            if branch is not None:
                completed = completed.filter(branch=branch)
            todays = [s for s in completed if s.created_at.date() == today]
            monthly = [s for s in completed if s.created_at.date() >= month_start]
            data["todays_sales"] = len(todays)
            data["monthly_sales"] = len(monthly)
            data["sales_value"] = sum((s.grand_total for s in monthly), Decimal("0.00"))
            # Profit = revenue minus cost of goods sold. Uses each line's
            # snapshotted sale price against the medicine's current cost —
            # good enough for a dashboard indicator; the Phase 5 profit
            # report will do this properly per purchase batch.
            # Profit uses each line's recorded batch cost (FEFO, fixed at sale
            # time) and revenue NET OF VAT — VAT is collected for the tax
            # authority and was never margin. Falls back to the medicine's
            # headline cost only for legacy lines with no recorded cost.
            profit = Decimal("0.00")
            for sale in monthly:
                for item in sale.items.all():
                    if item.unit_cost:
                        cost = item.line_cost
                    else:
                        cost = (item.medicine.purchase_price or Decimal("0.00")) * item.quantity
                    profit += item.line_after_discount - cost
            data["profit_summary"] = profit.quantize(Decimal("0.01"))
        return data

    def _purchase_kpis(self, branch=None):
        data = {"purchase_value": 0}
        if django_apps.is_installed("apps.purchases"):
            PurchaseInvoice = django_apps.get_model("purchases", "PurchaseInvoice")
            invoices = PurchaseInvoice.objects.prefetch_related("items")
            if branch is not None:
                invoices = invoices.filter(branch=branch)
            data["purchase_value"] = sum(
                (invoice.total_amount for invoice in invoices), Decimal("0.00")
            )
        return data

    @staticmethod
    def _for_branch(qs, branch):
        """Restricts a Sale queryset to one branch. Used by every chart so a
        branch view cannot accidentally mix in another branch's takings."""
        return qs if branch is None else qs.filter(branch=branch)

    def _chart_data(self, branch=None):
        """Structure consumed by Chart.js on the dashboard template."""
        charts = {
            "monthly_sales": {"labels": [], "values": []},
            "top_selling_medicines": {"labels": [], "values": []},
            "stock_by_category": {"labels": [], "values": []},
            "sales_trend": {"labels": [], "values": []},
            # Analytical charts
            "payment_mix": {"labels": [], "values": []},
            "revenue_vs_cost": {"labels": [], "revenue": [], "cost": []},
            "top_customers": {"labels": [], "values": []},
            "staff_performance": {"labels": [], "values": []},
            "expiry_risk": {"labels": [], "values": [], "value_at_risk": []},
        }

        if django_apps.is_installed("apps.medicine"):
            Category = django_apps.get_model("medicine", "Category")
            rows = (
                Category.objects.annotate(total_stock=Sum("medicines__quantity"))
                .values_list("name", "total_stock")
                .order_by("-total_stock")[:6]
            )
            charts["stock_by_category"]["labels"] = [r[0] for r in rows]
            charts["stock_by_category"]["values"] = [int(r[1] or 0) for r in rows]

        if django_apps.is_installed("apps.sales"):
            Sale = django_apps.get_model("sales", "Sale")
            SaleItem = django_apps.get_model("sales", "SaleItem")
            today = timezone.localdate()

            # Monthly sales: revenue per month over the last 6 months.
            for offset in range(5, -1, -1):
                year, month = today.year, today.month - offset
                while month <= 0:
                    month += 12
                    year -= 1
                sales = self._for_branch(Sale.objects.filter(
                    status="COMPLETED", created_at__year=year, created_at__month=month
                ).prefetch_related("items"), branch)
                charts["monthly_sales"]["labels"].append(date(year, month, 1).strftime("%b %Y"))
                charts["monthly_sales"]["values"].append(
                    float(sum((s.grand_total for s in sales), Decimal("0.00")))
                )

            # Sales trend: revenue per day over the last 14 days.
            for offset in range(13, -1, -1):
                day = today - timedelta(days=offset)
                sales = self._for_branch(Sale.objects.filter(
                    status="COMPLETED", created_at__date=day
                ).prefetch_related("items"), branch)
                charts["sales_trend"]["labels"].append(day.strftime("%d %b"))
                charts["sales_trend"]["values"].append(
                    float(sum((s.grand_total for s in sales), Decimal("0.00")))
                )

            # Top selling medicines by units sold (completed sales only).
            top_qs = SaleItem.objects.filter(sale__status="COMPLETED")
            if branch is not None:
                top_qs = top_qs.filter(sale__branch=branch)
            top = (
                top_qs
                .values("medicine_name")
                .annotate(units=Sum("quantity"))
                .order_by("-units")[:7]
            )
            charts["top_selling_medicines"]["labels"] = [r["medicine_name"] for r in top]
            charts["top_selling_medicines"]["values"] = [int(r["units"]) for r in top]

            # --- Analytical charts (Administrator-only dashboard) ---------

            # Payment method mix, by revenue rather than transaction count —
            # tells you where the money actually arrives.
            method_labels = dict(
                django_apps.get_model("sales", "Sale")._meta.get_field("payment_method").choices
            )
            mix = {}
            for sale in self._for_branch(
                Sale.objects.filter(status="COMPLETED").prefetch_related("items"), branch
            ):
                key = str(method_labels.get(sale.payment_method, sale.payment_method))
                mix[key] = mix.get(key, Decimal("0.00")) + sale.grand_total
            charts["payment_mix"]["labels"] = list(mix.keys())
            charts["payment_mix"]["values"] = [float(v) for v in mix.values()]

            # Revenue vs cost of goods sold per month — the margin trend,
            # which is the single most useful figure on this page.
            for offset in range(5, -1, -1):
                year, month = today.year, today.month - offset
                while month <= 0:
                    month += 12
                    year -= 1
                sales = self._for_branch(Sale.objects.filter(
                    status="COMPLETED", created_at__year=year, created_at__month=month
                ).prefetch_related("items__medicine"), branch)
                revenue, cost = Decimal("0.00"), Decimal("0.00")
                for sale in sales:
                    for item in sale.items.all():
                        revenue += item.line_total
                        cost += (item.medicine.purchase_price or Decimal("0.00")) * item.quantity
                charts["revenue_vs_cost"]["labels"].append(date(year, month, 1).strftime("%b"))
                charts["revenue_vs_cost"]["revenue"].append(float(revenue))
                charts["revenue_vs_cost"]["cost"].append(float(cost))

            # Top customers by lifetime spend — who is worth retaining.
            spend = {}
            for sale in (
                self._for_branch(
                    Sale.objects.filter(status="COMPLETED", customer__isnull=False), branch
                )
                .select_related("customer")
                .prefetch_related("items")
            ):
                spend[sale.customer.name] = spend.get(sale.customer.name, Decimal("0.00")) + sale.grand_total
            top_customers = sorted(spend.items(), key=lambda kv: kv[1], reverse=True)[:6]
            charts["top_customers"]["labels"] = [c[0] for c in top_customers]
            charts["top_customers"]["values"] = [float(c[1]) for c in top_customers]

            # Sales performance by staff member (revenue served).
            staff = {}
            for sale in (
                self._for_branch(
                    Sale.objects.filter(status="COMPLETED", served_by__isnull=False), branch
                )
                .select_related("served_by")
                .prefetch_related("items")
            ):
                name = sale.served_by.get_full_name() or sale.served_by.username
                staff[name] = staff.get(name, Decimal("0.00")) + sale.grand_total
            staff_rows = sorted(staff.items(), key=lambda kv: kv[1], reverse=True)[:6]
            charts["staff_performance"]["labels"] = [s[0] for s in staff_rows]
            charts["staff_performance"]["values"] = [float(s[1]) for s in staff_rows]

        # Expiry risk profile — how much stock is already dead vs at risk.
        # Sits outside the sales block because it only needs the catalog.
        if django_apps.is_installed("apps.medicine"):
            Medicine = django_apps.get_model("medicine", "Medicine")
            today = timezone.localdate()
            active = Medicine.objects.filter(is_active=True)
            buckets = [
                ("Expired", active.filter(expiry_date__lt=today)),
                ("≤ 30 days", active.filter(
                    expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))),
                ("31–60 days", active.filter(
                    expiry_date__gt=today + timedelta(days=30),
                    expiry_date__lte=today + timedelta(days=60))),
                ("61–180 days", active.filter(
                    expiry_date__gt=today + timedelta(days=60),
                    expiry_date__lte=today + timedelta(days=180))),
                ("> 180 days", active.filter(expiry_date__gt=today + timedelta(days=180))),
            ]
            charts["expiry_risk"]["labels"] = [b[0] for b in buckets]
            charts["expiry_risk"]["values"] = [b[1].count() for b in buckets]
            # Money at risk, not just item count — an expired box of cheap
            # tablets is not the same problem as expired insulin.
            charts["expiry_risk"]["value_at_risk"] = [
                float(sum(
                    (m.purchase_price or Decimal("0.00")) * m.quantity for m in b[1]
                ))
                for b in buckets
            ]

        return charts

