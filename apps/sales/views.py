"""
Sales / POS views.

Access (see apps.accounts.models.User):
  - can_operate_pos: Administrator, Cashier, Pharmacist. The Store Manager
    is deliberately excluded — the inverse of Purchases, where they're the
    primary role. Their job is stock and purchasing, not the till.
  - can_view_sales: everyone (Cashiers reprint receipts, Store Managers
    read sales figures to plan reordering).
  - can_void_sales: Administrator only — voiding returns stock and
    reverses a financial record.
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.permissions import RoleRequiredMixin, role_required
from apps.customers.models import Customer
from apps.medicine.models import Medicine

from .models import PaymentMethod, Sale, SaleStatus
from .services import complete_sale, void_sale

POS_ROLES = ["CASHIER", "PHARMACIST"]  # Administrator always passes


def _branch_qty(medicine, branch):
    """Stock at the till's own branch, for the POS lookup response."""
    if branch is None:
        return medicine.quantity or 0
    row = next(
        (bs for bs in medicine.branch_stocks.all() if bs.branch_id == branch.pk), None
    )
    if row is not None:
        return row.quantity
    from apps.branches.models import BranchStock

    obj = BranchStock.objects.filter(branch=branch, medicine=medicine).first()
    return obj.quantity if obj else 0
VOID_ROLES = []  # Administrator only


class POSView(RoleRequiredMixin, TemplateView):
    """The point-of-sale terminal. The cart lives in the browser (JS) and is
    posted as JSON to `pos_checkout` — deliberately not in the session, so
    two staff sharing a workstation can't inherit each other's cart."""

    template_name = "sales/pos.html"
    allowed_roles = POS_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["customers"] = Customer.objects.order_by("name")
        context["payment_methods"] = PaymentMethod.choices
        return context


@role_required("CASHIER", "PHARMACIST")
def medicine_lookup(request):
    """AJAX endpoint powering barcode scanning and auto-complete search in
    the POS. Returns only what the till needs — notably NOT purchase_price,
    since Cashiers and Pharmacists are not permitted to see cost data."""
    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse({"results": []})

    branch = getattr(request, "branch", None)
    stock_filter = {"is_active": True}
    medicines = (
        Medicine.objects.filter(**stock_filter)
        .filter(
            Q(barcode__iexact=query)
            | Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(generic_name__icontains=query)
        )
        .select_related("category")
    )
    # Only offer what this branch actually holds. Showing another branch's
    # stock at the till would produce a confident search result that then
    # fails at checkout.
    if branch is not None:
        medicines = medicines.filter(
            branch_stocks__branch=branch, branch_stocks__quantity__gt=0
        ).distinct()
    else:
        medicines = medicines.filter(quantity__gt=0)
    medicines = medicines[:15]

    results = [
        {
            "id": m.pk,
            "code": m.code,
            "name": m.name,
            "generic_name": m.generic_name,
            "unit": m.get_unit_display(),
            "selling_price": str(m.selling_price),
            "tax_percent": str(m.tax_percent),
            "discount_percent": str(m.discount_percent),
            "quantity_available": _branch_qty(m, branch),
            "is_expired": m.is_expired,
            "product_type": m.get_product_type_display(),
            "requires_prescription": m.requires_prescription,
        }
        for m in medicines
    ]
    return JsonResponse({"results": results})


@role_required("CASHIER", "PHARMACIST")
def pos_checkout(request):
    """Completes a sale from the JSON cart posted by the POS."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    raw_cart = payload.get("cart") or []
    cart = []
    for row in raw_cart:
        try:
            quantity = int(row["quantity"])
            discount = Decimal(str(row.get("discount_percent") or "0"))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return JsonResponse({"error": _("Invalid cart line.")}, status=400)
        # Reject nonsense values here rather than letting them reach the
        # database, where a negative quantity used to raise IntegrityError
        # and surface as a 500 instead of a readable message.
        if quantity < 1:
            return JsonResponse(
                {"error": _("Quantity must be at least 1 for every item.")}, status=400
            )
        if discount < 0 or discount > 100:
            return JsonResponse(
                {"error": _("Discount must be between 0 and 100 percent.")}, status=400
            )
        try:
            cart.append({
                "medicine_id": int(row["medicine_id"]),
                "quantity": quantity,
                "discount_percent": discount,
            })
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"error": _("Invalid cart line.")}, status=400)

    if len(cart) > 200:
        return JsonResponse({"error": _("Too many items in one sale.")}, status=400)

    customer = None
    if payload.get("customer_id"):
        customer = Customer.objects.filter(pk=payload["customer_id"]).first()

    payment_method = payload.get("payment_method") or PaymentMethod.CASH
    if payment_method not in dict(PaymentMethod.choices):
        return JsonResponse({"error": "Unknown payment method."}, status=400)

    try:
        amount_paid = Decimal(str(payload.get("amount_paid") or "0"))
    except InvalidOperation:
        return JsonResponse({"error": _("Invalid amount paid.")}, status=400)
    if amount_paid < 0:
        return JsonResponse({"error": _("Amount paid cannot be negative.")}, status=400)

    try:
        sale = complete_sale(
            cart=cart,
            customer=customer,
            payment_method=payment_method,
            amount_paid=amount_paid,
            user=request.user,
            branch=getattr(request, "branch", None),
            notes=payload.get("notes") or "",
        )
    except ValidationError as e:
        return JsonResponse({"error": "; ".join(e.messages)}, status=400)

    return JsonResponse(
        {
            "success": True,
            "sale_id": sale.pk,
            "invoice_number": sale.invoice_number,
            "grand_total": str(sale.grand_total),
            "change_due": str(sale.change_due),
            "invoice_url": sale.get_absolute_url(),
        }
    )


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "sales/sale_list.html"
    context_object_name = "sales"
    paginate_by = 25

    def get_queryset(self):
        from apps.branches.context import branch_scope

        qs = Sale.objects.select_related("customer", "served_by", "branch").prefetch_related("items")
        qs = branch_scope(qs, self.request)
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            qs = qs.filter(
                Q(invoice_number__icontains=query) | Q(customer__name__icontains=query)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        completed_today = Sale.objects.filter(created_at__date=today, status=SaleStatus.COMPLETED)
        context["todays_count"] = completed_today.count()
        context["todays_total"] = sum((s.grand_total for s in completed_today), Decimal("0.00"))
        context["can_void"] = self.request.user.can_void_sales()
        context["can_operate_pos"] = self.request.user.can_operate_pos()
        return context


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = "sales/sale_detail.html"
    context_object_name = "sale"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_void"] = self.request.user.can_void_sales()
        return context


class SaleInvoiceView(LoginRequiredMixin, DetailView):
    """Printable A5-ish receipt/invoice. Available to any logged-in role so
    a Cashier can reprint a customer's receipt."""

    model = Sale
    template_name = "sales/sale_invoice.html"
    context_object_name = "sale"


@role_required()  # empty role list + Administrator bypass = Administrator only
def sale_void(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST":
        try:
            void_sale(sale=sale, user=request.user, reason=request.POST.get("reason", ""))
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect("sales:sale_detail", pk=sale.pk)
        messages.success(
            request, f"Sale {sale.invoice_number} voided — stock has been returned."
        )
        return redirect("sales:sale_detail", pk=sale.pk)
    return render(request, "sales/sale_confirm_void.html", {"sale": sale})
