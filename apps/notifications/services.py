"""
Notification generation.

`refresh_notifications()` scans current state and creates/resolves alerts.
It is idempotent — safe to call from a scheduled task, a management command,
or (cheaply, see `refresh_if_stale`) on page load.

Alerts are created by *condition*, and resolved automatically when the
condition clears: replenish a low-stock medicine and its warning disappears
rather than lingering until someone dismisses it. Event-style alerts (new
purchase, large sale) are created once by signals and are not resolved,
because the event genuinely happened.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Notification, NotificationType, Severity

#: A sale at or above this value raises a "large sale" alert. Kept here so
#: the Settings module can promote it to a DB field without touching logic.
LARGE_SALE_THRESHOLD = Decimal("1000.00")

#: Skip a full rescan if one ran within this window — keeps the navbar
#: cheap when it triggers a refresh on page load.
REFRESH_INTERVAL = timedelta(minutes=10)

MANAGER_ROLES = "ADMIN,STORE_MANAGER"
STOCK_ROLES = "ADMIN,STORE_MANAGER,PHARMACIST"


def _upsert(dedupe_key, **fields):
    """Creates the alert or reactivates/updates an existing one."""
    notification, created = Notification.objects.get_or_create(
        dedupe_key=dedupe_key, defaults=fields
    )
    if not created:
        changed = []
        for key, value in fields.items():
            if getattr(notification, key) != value:
                setattr(notification, key, value)
                changed.append(key)
        if not notification.is_active:
            notification.is_active = True
            notification.resolved_at = None
            changed += ["is_active", "resolved_at"]
        if changed:
            notification.save(update_fields=changed)
    return notification


def refresh_notifications():
    """Rebuilds condition-based alerts. Returns a counts summary."""
    from apps.medicine.models import Medicine

    today = timezone.localdate()
    seen_keys = set()

    # ---- Low stock, per branch ----------------------------------------
    # Alerts are raised per (branch, product): a product short in Gondar must
    # still be flagged even if Bole is well stocked, which a pharmacy-wide
    # total would hide entirely.
    from apps.branches.models import BranchStock

    low = (
        BranchStock.objects.filter(
            medicine__is_active=True, quantity__lte=F("reorder_level")
        ).select_related("medicine", "branch")
    )
    for row in low:
        m, branch = row.medicine, row.branch
        key = f"low_stock:{branch.pk}:{m.pk}"
        seen_keys.add(key)
        out_of_stock = row.quantity == 0
        _upsert(
            key,
            notification_type=NotificationType.LOW_STOCK,
            severity=Severity.CRITICAL if out_of_stock else Severity.WARNING,
            title=(_("Out of stock at %(branch)s: %(name)s") if out_of_stock
                   else _("Low stock at %(branch)s: %(name)s"))
            % {"name": m.name, "branch": branch.name},
            message=_("%(qty)s in stock at %(branch)s, reorder level is %(level)s.") % {
                "qty": row.quantity, "branch": branch.name, "level": row.reorder_level},
            link=reverse("medicine:medicine_detail", kwargs={"pk": m.pk}),
            target_roles=STOCK_ROLES,
            branch=branch,
        )

    # ---- Expired / expiring ------------------------------------------
    horizon = today + timedelta(days=60)
    for m in Medicine.objects.filter(is_active=True, expiry_date__lte=horizon):
        expired = m.expiry_date < today
        days = (m.expiry_date - today).days
        key = f"{'expired' if expired else 'expiring'}:{m.pk}"
        seen_keys.add(key)
        if expired:
            title = _("Expired: %(name)s") % {"name": m.name}
            message = _("Expired on %(date)s. %(qty)s units still in stock.") % {
                "date": m.expiry_date, "qty": m.quantity}
            severity, ntype = Severity.CRITICAL, NotificationType.EXPIRED
        else:
            title = _("Expiring soon: %(name)s") % {"name": m.name}
            message = _("Expires on %(date)s (in %(days)s days).") % {
                "date": m.expiry_date, "days": days}
            severity = Severity.WARNING if days <= 30 else Severity.INFO
            ntype = NotificationType.EXPIRING
        _upsert(
            key, notification_type=ntype, severity=severity, title=title,
            message=message,
            link=reverse("medicine:medicine_detail", kwargs={"pk": m.pk}),
            target_roles=STOCK_ROLES,
        )

    # ---- Pending payments --------------------------------------------
    # A completed sale where the customer paid less than the total is an
    # outstanding balance that someone needs to chase.
    from apps.sales.models import Sale, SaleStatus

    for sale in Sale.objects.filter(status=SaleStatus.COMPLETED).prefetch_related("items"):
        outstanding = sale.grand_total - sale.amount_paid
        key = f"pending_payment:{sale.pk}"
        if outstanding > Decimal("0.00"):
            seen_keys.add(key)
            _upsert(
                key,
                notification_type=NotificationType.PENDING_PAYMENT,
                severity=Severity.WARNING,
                title=_("Pending payment: %(inv)s") % {"inv": sale.invoice_number},
                message=_("Outstanding balance of %(amount)s on %(customer)s.") % {
                    "amount": outstanding,
                    "customer": sale.customer.name if sale.customer else _("a walk-in sale"),
                },
                link=reverse("sales:sale_detail", kwargs={"pk": sale.pk}),
                target_roles=MANAGER_ROLES,
                branch=sale.branch,
            )

    # ---- Resolve conditions that no longer hold -----------------------
    stale = Notification.objects.filter(
        is_active=True,
        notification_type__in=[
            NotificationType.LOW_STOCK, NotificationType.EXPIRED,
            NotificationType.EXPIRING, NotificationType.PENDING_PAYMENT,
        ],
    ).exclude(dedupe_key__in=seen_keys)
    resolved = stale.count()
    for notification in stale:
        notification.resolve()

    return {"active": len(seen_keys), "resolved": resolved}


def notify_new_purchase(invoice):
    """Event alert — a purchase happened; not auto-resolved."""
    _upsert(
        f"new_purchase:{invoice.pk}",
        notification_type=NotificationType.NEW_PURCHASE,
        severity=Severity.INFO,
        title=_("New purchase recorded: %(num)s") % {"num": invoice.purchase_number},
        message=_("%(supplier)s — %(total)s across %(items)s item(s). Stock has been increased.") % {
            "supplier": invoice.supplier.name,
            "total": invoice.total_amount,
            "items": invoice.total_items,
        },
        link=reverse("purchases:purchase_detail", kwargs={"pk": invoice.pk}),
        target_roles=MANAGER_ROLES,
        branch=invoice.branch,
    )


def notify_large_sale(sale):
    """Event alert for a sale at or above LARGE_SALE_THRESHOLD."""
    _upsert(
        f"large_sale:{sale.pk}",
        notification_type=NotificationType.LARGE_SALE,
        severity=Severity.INFO,
        title=_("Large sale: %(inv)s") % {"inv": sale.invoice_number},
        message=_("%(total)s in a single transaction, served by %(user)s.") % {
            "total": sale.grand_total,
            "user": (sale.served_by.get_full_name() or sale.served_by.username)
                    if sale.served_by else _("unknown"),
        },
        link=reverse("sales:sale_detail", kwargs={"pk": sale.pk}),
        target_roles=MANAGER_ROLES,
        branch=sale.branch,
    )


def unread_for_user(user, limit=None, branch=None):
    """Active notifications for this user that they haven't read.

    Branch-specific alerts are only shown to people who work at that branch
    (Administrators see everything). Alerts with no branch — pharmacy-wide
    or legacy — are shown to everyone whose role matches.
    """
    qs = Notification.objects.filter(is_active=True).exclude(reads__user=user)
    items = [n for n in qs if n.is_for_user(user)]
    if not user.can_access_all_branches():
        allowed = {user.branch_id} if user.branch_id else set()
        items = [n for n in items if n.branch_id is None or n.branch_id in allowed]
    elif branch is not None:
        items = [n for n in items if n.branch_id in (None, branch.pk)]
    return items[:limit] if limit else items


def refresh_if_stale():
    """Cheap guard so a page-load refresh doesn't rescan on every request."""
    latest = Notification.objects.order_by("-created_at").values_list(
        "created_at", flat=True
    ).first()
    if latest is None or timezone.now() - latest > REFRESH_INTERVAL:
        refresh_notifications()
