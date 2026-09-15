"""
Report registry.

Every report is a small class declaring four things: who may see it, what
columns it has, how to build its rows from a set of filters, and (optionally)
summary totals. The HTML view and the CSV / Excel / PDF exporters are all
generic and driven from that declaration — so adding a report means adding
one class here, not four new views and four new templates.

Access control is per-report (`allowed_roles`), not per-section. A Cashier
reaching /reports/ sees the sales and customer reports; the purchase and
profit reports aren't listed for them and 403 on direct URL access.
`COST_ROLES` reports additionally expose purchase prices and margins.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.customers.models import Customer
from apps.medicine.models import Category, Medicine
from apps.purchases.models import PurchaseInvoice
from apps.sales.models import Sale, SaleItem, SaleStatus
from apps.suppliers.models import Supplier

# Role sets. Administrator always passes via RoleRequiredMixin, so it is
# intentionally absent from these lists.
ALL_ROLES = ["STORE_MANAGER", "PHARMACIST", "CASHIER"]
STOCK_ROLES = ["STORE_MANAGER", "PHARMACIST"]
COST_ROLES = ["STORE_MANAGER"]


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


class BaseReport:
    """Subclasses declare slug/title/columns and implement get_rows()."""

    slug = ""
    title = ""
    description = ""
    icon = "fa-chart-line"
    allowed_roles = ALL_ROLES
    #: Which filter widgets the template should render for this report.
    #: Supported: "date_range", "period", "category", "supplier", "branch"
    filters = ["date_range"]
    #: Whether this report's figures are branch-specific. Sales, purchases,
    #: profit and stock all are. Supplier and customer records are shared
    #: across the pharmacy, so those reports ignore branch entirely.
    branch_scoped = True
    #: Column definitions: (header, alignment) where alignment is l/r
    columns = []

    def get_rows(self, filters):
        """Returns a list of row lists, matching `columns` in order."""
        raise NotImplementedError

    def get_summary(self, filters):
        """Optional: list of (label, value) shown above the table and in
        exports. Default: no summary."""
        return []

    # -- filter helpers shared by subclasses -----------------------------
    @staticmethod
    def branch(filters):
        """The branch to report on, or None for the whole pharmacy.

        `_branch` is set by the view from the user's own access: a
        branch-assigned user can only ever get their own branch here, so a
        report cannot leak another branch's figures.
        """
        return filters.get("_branch")

    @staticmethod
    def date_bounds(filters):
        """Resolves date_from / date_to, defaulting to the current month."""
        today = timezone.localdate()
        date_from = filters.get("date_from") or today.replace(day=1)
        date_to = filters.get("date_to") or today
        return date_from, date_to


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
class SalesReport(BaseReport):
    slug = "sales"
    title = _("Sales Report")
    description = _("Every completed sale in the period, with totals.")
    icon = "fa-receipt"
    allowed_roles = ALL_ROLES
    filters = ["date_range", "period", "branch"]
    columns = [
        (_("Invoice"), "l"), (_("Branch"), "l"), (_("Date"), "l"), (_("Customer"), "l"),
        (_("Items"), "r"), (_("Payment"), "l"), (_("Subtotal"), "r"),
        (_("Discount"), "r"), (_("VAT"), "r"), (_("Total"), "r"),
        (_("Served By"), "l"),
    ]

    def _queryset(self, filters):
        date_from, date_to = self.date_bounds(filters)
        qs = (
            Sale.objects.filter(
                status=SaleStatus.COMPLETED,
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            )
            .select_related("customer", "served_by", "branch")
            .prefetch_related("items")
            .order_by("created_at")
        )
        branch = self.branch(filters)
        if branch is not None:
            qs = qs.filter(branch=branch)
        return qs

    def get_rows(self, filters):
        rows = []
        for s in self._queryset(filters):
            rows.append([
                s.invoice_number,
                s.branch.name if s.branch else "—",
                s.created_at.strftime("%Y-%m-%d %H:%M"),
                s.customer.name if s.customer else str(_("Walk-in")),
                s.total_units,
                s.get_payment_method_display(),
                _money(s.subtotal),
                _money(s.total_discount),
                _money(s.total_vat),
                _money(s.grand_total),
                (s.served_by.get_full_name() or s.served_by.username) if s.served_by else "—",
            ])
        return rows

    def get_summary(self, filters):
        sales = list(self._queryset(filters))
        revenue = sum((s.grand_total for s in sales), Decimal("0.00"))
        return [
            (_("Transactions"), len(sales)),
            (_("Units Sold"), sum(s.total_units for s in sales)),
            (_("Total Discount"), _money(sum((s.total_discount for s in sales), Decimal("0.00")))),
            (_("Total VAT"), _money(sum((s.total_vat for s in sales), Decimal("0.00")))),
            (_("Total Revenue"), _money(revenue)),
        ]


class SalesSummaryReport(BaseReport):
    """Sales aggregated by day / week / month / year — the "Daily, Weekly,
    Monthly, Yearly" breakdown, driven by one `period` filter rather than
    four near-identical reports."""

    slug = "sales-summary"
    title = _("Sales Summary (Daily / Weekly / Monthly / Yearly)")
    description = _("Revenue grouped by period, for trend and comparison.")
    icon = "fa-calendar-days"
    allowed_roles = ALL_ROLES
    filters = ["date_range", "period", "branch"]
    columns = [
        (_("Period"), "l"), (_("Transactions"), "r"), (_("Units Sold"), "r"),
        (_("Discount"), "r"), (_("VAT"), "r"), (_("Revenue"), "r"),
    ]

    PERIOD_FORMATS = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m",
        "year": "%Y",
    }

    def get_rows(self, filters):
        date_from, date_to = self.date_bounds(filters)
        period = filters.get("period") or "day"
        fmt = self.PERIOD_FORMATS.get(period, "%Y-%m-%d")

        buckets = {}
        sales = (
            Sale.objects.filter(
                status=SaleStatus.COMPLETED,
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            ).prefetch_related("items")
        )
        branch = self.branch(filters)
        if branch is not None:
            sales = sales.filter(branch=branch)
        for s in sales:
            key = timezone.localtime(s.created_at).strftime(fmt)
            b = buckets.setdefault(key, {"n": 0, "units": 0, "disc": Decimal("0.00"),
                                         "vat": Decimal("0.00"), "rev": Decimal("0.00")})
            b["n"] += 1
            b["units"] += s.total_units
            b["disc"] += s.total_discount
            b["vat"] += s.total_vat
            b["rev"] += s.grand_total

        return [
            [key, b["n"], b["units"], _money(b["disc"]), _money(b["vat"]), _money(b["rev"])]
            for key, b in sorted(buckets.items())
        ]

    def get_summary(self, filters):
        rows = self.get_rows(filters)
        return [
            (_("Periods"), len(rows)),
            (_("Total Revenue"), _money(sum((r[5] for r in rows), Decimal("0.00")))),
        ]


# ---------------------------------------------------------------------------
# Purchases & profit (cost-sensitive)
# ---------------------------------------------------------------------------
class PurchaseReport(BaseReport):
    slug = "purchases"
    title = _("Purchase Report")
    description = _("Supplier purchases in the period, with invoice totals.")
    icon = "fa-cart-shopping"
    allowed_roles = COST_ROLES
    filters = ["date_range", "supplier", "branch"]
    columns = [
        (_("Purchase #"), "l"), (_("Date"), "l"), (_("Supplier"), "l"),
        (_("Items"), "r"), (_("Total"), "r"), (_("Recorded By"), "l"),
    ]

    def _queryset(self, filters):
        date_from, date_to = self.date_bounds(filters)
        qs = (
            PurchaseInvoice.objects.filter(
                purchase_date__gte=date_from, purchase_date__lte=date_to
            )
            .select_related("supplier", "recorded_by")
            .prefetch_related("items")
            .order_by("purchase_date")
        )
        if filters.get("supplier"):
            qs = qs.filter(supplier_id=filters["supplier"])
        branch = self.branch(filters)
        if branch is not None:
            qs = qs.filter(branch=branch)
        return qs

    def get_rows(self, filters):
        return [
            [
                p.purchase_number,
                p.purchase_date.strftime("%Y-%m-%d"),
                p.supplier.name,
                p.total_items,
                _money(p.total_amount),
                (p.recorded_by.get_full_name() or p.recorded_by.username) if p.recorded_by else "—",
            ]
            for p in self._queryset(filters)
        ]

    def get_summary(self, filters):
        invoices = list(self._queryset(filters))
        return [
            (_("Invoices"), len(invoices)),
            (_("Total Purchase Value"),
             _money(sum((p.total_amount for p in invoices), Decimal("0.00")))),
        ]


class ProfitReport(BaseReport):
    slug = "profit"
    title = _("Profit Report")
    description = _("Revenue against actual batch cost of goods sold, per medicine.")
    icon = "fa-coins"
    allowed_roles = COST_ROLES
    filters = ["date_range", "branch"]
    columns = [
        (_("Medicine"), "l"), (_("Units Sold"), "r"), (_("Revenue (excl. VAT)"), "r"),
        (_("Cost of Goods"), "r"), (_("Gross Profit"), "r"), (_("Margin %"), "r"),
    ]

    def _aggregate(self, filters):
        date_from, date_to = self.date_bounds(filters)
        items = (
            SaleItem.objects.filter(
                sale__status=SaleStatus.COMPLETED,
                sale__created_at__date__gte=date_from,
                sale__created_at__date__lte=date_to,
            ).select_related("medicine")
        )
        branch = self.branch(filters)
        if branch is not None:
            items = items.filter(sale__branch=branch)
        agg = {}
        for item in items:
            row = agg.setdefault(item.medicine_name, {
                "units": 0, "revenue": Decimal("0.00"), "cost": Decimal("0.00")})
            row["units"] += item.quantity
            # Revenue net of VAT: VAT is collected for the tax authority and
            # was never margin, so including it would overstate profit.
            row["revenue"] += item.line_after_discount
            # Cost of goods from the batches actually consumed at sale time
            # (FEFO) — exact, and unaffected by later price changes. Falls
            # back to the medicine's headline cost only for legacy sales
            # recorded before batch tracking existed.
            if item.unit_cost:
                row["cost"] += item.line_cost
            else:
                row["cost"] += (item.medicine.purchase_price or Decimal("0.00")) * item.quantity
        return agg

    def get_rows(self, filters):
        rows = []
        for name, v in sorted(self._aggregate(filters).items(),
                              key=lambda kv: kv[1]["revenue"], reverse=True):
            profit = v["revenue"] - v["cost"]
            margin = (profit / v["revenue"] * 100) if v["revenue"] else Decimal("0")
            rows.append([
                name, v["units"], _money(v["revenue"]), _money(v["cost"]),
                _money(profit), f"{margin:.1f}",
            ])
        return rows

    def get_summary(self, filters):
        agg = self._aggregate(filters)
        revenue = sum((v["revenue"] for v in agg.values()), Decimal("0.00"))
        cost = sum((v["cost"] for v in agg.values()), Decimal("0.00"))
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue else Decimal("0")
        return [
            (_("Total Revenue"), _money(revenue)),
            (_("Total Cost of Goods"), _money(cost)),
            (_("Gross Profit"), _money(profit)),
            (_("Gross Margin %"), f"{margin:.1f}"),
        ]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
class InventoryReport(BaseReport):
    slug = "inventory"
    title = _("Inventory Report")
    description = _("Full stock position across the catalog.")
    icon = "fa-warehouse"
    allowed_roles = STOCK_ROLES
    filters = ["category", "branch"]
    columns = [
        (_("Code"), "l"), (_("Product"), "l"), (_("Category"), "l"),
        (_("Quantity"), "r"), (_("Reorder Level"), "r"), (_("Unit"), "l"),
        (_("Expiry Date"), "l"), (_("Stock Value"), "r"),
    ]

    def _queryset(self, filters):
        qs = Medicine.objects.select_related("category").order_by("name")
        if filters.get("category"):
            qs = qs.filter(category_id=filters["category"])
        branch = self.branch(filters)
        if branch is not None:
            # Only products actually stocked at this branch. Listing the whole
            # shared catalogue with zeros would bury the real stock position.
            qs = qs.filter(branch_stocks__branch=branch).distinct()
        return qs

    def _levels(self, filters):
        """(quantity, reorder_level) per product, per branch when one is set."""
        branch = self.branch(filters)
        if branch is None:
            return None
        from apps.branches.models import BranchStock

        return {
            row.medicine_id: row
            for row in BranchStock.objects.filter(branch=branch)
        }

    def get_rows(self, filters):
        show_value = filters.get("_can_view_cost", False)
        levels = self._levels(filters)
        rows = []
        for m in self._queryset(filters):
            if levels is not None:
                row = levels.get(m.pk)
                qty = row.quantity if row else 0
                reorder = row.reorder_level if row else m.reorder_level
            else:
                qty, reorder = m.quantity, m.reorder_level
            value = (m.purchase_price or Decimal("0.00")) * qty
            rows.append([
                m.code, m.name, m.category.name, qty, reorder,
                m.get_unit_display(),
                m.expiry_date.strftime("%Y-%m-%d") if m.expiry_date else "—",
                _money(value) if show_value else "—",
            ])
        return rows

    def get_summary(self, filters):
        rows = self.get_rows(filters)
        out = [
            (_("Products"), len(rows)),
            (_("Total Units in Stock"), sum(r[3] for r in rows)),
        ]
        if filters.get("_can_view_cost", False):
            total = sum((Decimal(str(r[7])) for r in rows if r[7] != "—"), Decimal("0.00"))
            out.append((_("Total Stock Value"), _money(total)))
        branch = self.branch(filters)
        if branch is not None:
            out.insert(0, (_("Branch"), branch.name))
        return out


class LowStockReport(BaseReport):
    slug = "low-stock"
    title = _("Low Stock Report")
    description = _("Medicines at or below their reorder level.")
    icon = "fa-triangle-exclamation"
    allowed_roles = STOCK_ROLES
    filters = ["branch"]
    columns = [
        (_("Code"), "l"), (_("Product"), "l"), (_("Branch"), "l"),
        (_("Quantity"), "r"), (_("Reorder Level"), "r"), (_("Supplier"), "l"),
    ]

    def get_rows(self, filters):
        branch = self.branch(filters)
        if branch is not None:
            # Compare against THIS branch's own reorder level, which may
            # legitimately differ from another branch's.
            from apps.branches.models import BranchStock

            rows = (
                BranchStock.objects.filter(
                    branch=branch, quantity__lte=F("reorder_level"),
                    medicine__is_active=True,
                )
                .select_related("medicine", "medicine__category", "medicine__supplier")
                .order_by("quantity")
            )
            return [
                [r.medicine.code, r.medicine.name, branch.name, r.quantity,
                 r.reorder_level,
                 r.medicine.supplier.name if r.medicine.supplier else "—"]
                for r in rows
            ]

        # Pharmacy-wide: every branch/product pair below its own level, so a
        # product short in one branch is not hidden by a surplus in another.
        from apps.branches.models import BranchStock

        rows = (
            BranchStock.objects.filter(
                quantity__lte=F("reorder_level"), medicine__is_active=True
            )
            .select_related("branch", "medicine", "medicine__category", "medicine__supplier")
            .order_by("medicine__name", "branch__name")
        )
        return [
            [r.medicine.code, r.medicine.name, r.branch.name, r.quantity,
             r.reorder_level,
             r.medicine.supplier.name if r.medicine.supplier else "—"]
            for r in rows
        ]

    def get_summary(self, filters):
        rows = self.get_rows(filters)
        return [
            (_("Needing Reorder"), len(rows)),
            (_("Out of Stock"), sum(1 for r in rows if r[3] == 0)),
        ]


class ExpiredMedicineReport(BaseReport):
    slug = "expiry"
    title = _("Expired & Expiring Medicine Report")
    description = _("Already expired, plus stock expiring within 30 and 60 days.")
    icon = "fa-calendar-xmark"
    allowed_roles = STOCK_ROLES
    filters = ["branch"]
    columns = [
        (_("Code"), "l"), (_("Product"), "l"), (_("Batch Number"), "l"),
        (_("Expiry Date"), "l"), (_("Status"), "l"), (_("Quantity"), "r"),
        (_("Value at Risk"), "r"),
    ]

    def get_rows(self, filters):
        today = timezone.localdate()
        show_value = filters.get("_can_view_cost", False)
        qs = (
            Medicine.objects.filter(
                is_active=True, expiry_date__lte=today + timedelta(days=60)
            )
            .select_related("category")
            .order_by("expiry_date")
        )
        branch = self.branch(filters)
        levels = None
        if branch is not None:
            from apps.branches.models import BranchStock

            qs = qs.filter(branch_stocks__branch=branch,
                           branch_stocks__quantity__gt=0).distinct()
            levels = {r.medicine_id: r.quantity
                      for r in BranchStock.objects.filter(branch=branch)}
        rows = []
        for m in qs:
            if m.expiry_date < today:
                status = _("Expired")
            elif (m.expiry_date - today).days <= 30:
                status = _("Expires within 30 days")
            else:
                status = _("Expires within 60 days")
            qty = levels.get(m.pk, 0) if levels is not None else m.quantity
            value = (m.purchase_price or Decimal("0.00")) * qty
            rows.append([
                m.code, m.name, m.batch_number or "—",
                m.expiry_date.strftime("%Y-%m-%d"), status, qty,
                _money(value) if show_value else "—",
            ])
        return rows

    def get_summary(self, filters):
        today = timezone.localdate()
        active = Medicine.objects.filter(is_active=True)
        return [
            (_("Expired"), active.filter(expiry_date__lt=today).count()),
            (_("Expiring within 30 days"), active.filter(
                expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30)).count()),
            (_("Expiring within 60 days"), active.filter(
                expiry_date__gt=today + timedelta(days=30),
                expiry_date__lte=today + timedelta(days=60)).count()),
        ]


# ---------------------------------------------------------------------------
# Partners
# ---------------------------------------------------------------------------
class SupplierReport(BaseReport):
    slug = "suppliers"
    title = _("Supplier Report")
    description = _("Suppliers with medicines supplied and purchase totals.")
    icon = "fa-truck-field"
    allowed_roles = STOCK_ROLES
    filters = ["date_range"]
    branch_scoped = False  # suppliers are shared across the pharmacy
    columns = [
        (_("Supplier"), "l"), (_("Contact Person"), "l"), (_("Phone"), "l"),
        (_("Status"), "l"), (_("Medicines Supplied"), "r"),
        (_("Purchase Invoices"), "r"), (_("Purchase Value"), "r"),
    ]

    def get_rows(self, filters):
        date_from, date_to = self.date_bounds(filters)
        show_value = filters.get("_can_view_cost", False)
        rows = []
        for s in Supplier.objects.prefetch_related("medicines").order_by("name"):
            invoices = list(
                s.purchase_invoices.filter(
                    purchase_date__gte=date_from, purchase_date__lte=date_to
                ).prefetch_related("items")
            )
            total = sum((i.total_amount for i in invoices), Decimal("0.00"))
            rows.append([
                s.name, s.contact_person or "—", s.phone,
                s.get_status_display(), s.medicine_count, len(invoices),
                _money(total) if show_value else "—",
            ])
        return rows

    def get_summary(self, filters):
        return [
            (_("Suppliers"), Supplier.objects.count()),
            (_("Active"), Supplier.objects.filter(status=Supplier.Status.ACTIVE).count()),
        ]


class CustomerReport(BaseReport):
    slug = "customers"
    title = _("Customer Report")
    description = _("Customers with purchase history and loyalty points.")
    icon = "fa-users"
    allowed_roles = ALL_ROLES
    filters = ["date_range"]
    branch_scoped = False  # one customer record serves every branch
    columns = [
        (_("Customer"), "l"), (_("Phone"), "l"), (_("Email"), "l"),
        (_("Loyalty Points"), "r"), (_("Purchases"), "r"), (_("Total Spend"), "r"),
    ]

    def get_rows(self, filters):
        date_from, date_to = self.date_bounds(filters)
        rows = []
        for c in Customer.objects.order_by("name"):
            sales = list(
                c.sales.filter(
                    status=SaleStatus.COMPLETED,
                    created_at__date__gte=date_from,
                    created_at__date__lte=date_to,
                ).prefetch_related("items")
            )
            spend = sum((s.grand_total for s in sales), Decimal("0.00"))
            rows.append([
                c.name, c.phone, c.email or "—", c.loyalty_points,
                len(sales), _money(spend),
            ])
        return rows

    def get_summary(self, filters):
        return [
            (_("Customers"), Customer.objects.count()),
            (_("Total Loyalty Points"),
             Customer.objects.aggregate(t=Sum("loyalty_points"))["t"] or 0),
        ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
REPORTS = {
    r.slug: r for r in [
        SalesReport,
        SalesSummaryReport,
        PurchaseReport,
        ProfitReport,
        InventoryReport,
        LowStockReport,
        ExpiredMedicineReport,
        SupplierReport,
        CustomerReport,
    ]
}


def get_report(slug):
    report_class = REPORTS.get(slug)
    return report_class() if report_class else None


def reports_for_user(user):
    """Only the reports this user's role is allowed to open."""
    return [
        r for r in REPORTS.values()
        if user.is_administrator or user.role in r.allowed_roles
    ]
