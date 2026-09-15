"""
Stocktake posting and reorder suggestions.

Stocktake
---------
`open_stocktake` freezes the expected quantity for everything in scope.
`post_stocktake` turns the counted figures into real adjustments, one per
line that differs, so the batch ledger and the stock ledger both stay in
step. Uncounted lines are skipped rather than treated as zero — the single
most dangerous default this feature could have had, since it would wipe out
stock nobody got round to counting.

Reorder suggestions
-------------------
A reorder level alone tells you *that* something is low, not *how much* to
buy. `reorder_suggestions` adds consumption: it measures units sold per day
over a recent window, works out how many days of cover remain, and suggests
an order quantity that restores a target number of days. A product with no
sales history falls back to topping up to the reorder level, because
suggesting nothing for a dead-stock item that has genuinely run out would be
worse than a rough guess.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

#: Window used to measure sales velocity. Long enough to smooth out a quiet
#: week, short enough to react to a real change in demand.
VELOCITY_WINDOW_DAYS = 60

#: How many days of stock a suggested order should restore.
TARGET_DAYS_OF_COVER = 45


@transaction.atomic
def open_stocktake(*, branch, category=None, user=None, note=""):
    """Creates a stocktake and freezes the expected figures."""
    from apps.branches.models import BranchStock

    from .stocktake import StockTake, StockTakeLine, StockTakeStatus

    if branch is None:
        raise ValidationError(_("A branch is required to start a stocktake."))

    existing = StockTake.objects.filter(
        branch=branch, status=StockTakeStatus.DRAFT
    ).first()
    if existing:
        # Two open counts on one branch would produce contradictory
        # adjustments from the same shelf, so only one is allowed at a time.
        raise ValidationError(
            _("%(ref)s is already in progress for %(branch)s. Finish or cancel it "
              "first.") % {"ref": existing.reference, "branch": branch.name}
        )

    stocktake = StockTake.objects.create(
        branch=branch, category=category, started_by=user, note=note
    )

    rows = BranchStock.objects.filter(
        branch=branch, medicine__is_active=True
    ).select_related("medicine")
    if category is not None:
        rows = rows.filter(medicine__category=category)

    StockTakeLine.objects.bulk_create([
        StockTakeLine(
            stocktake=stocktake, medicine_id=row.medicine_id,
            expected_quantity=row.quantity,
        )
        for row in rows
    ])
    return stocktake


@transaction.atomic
def post_stocktake(*, stocktake, user=None):
    """Applies the counted figures as adjustments.

    Returns a summary dict. Only lines that were actually counted *and*
    differ from the expected figure produce a movement, which keeps the
    ledger readable — a stocktake that confirmed 400 correct products should
    not add 400 no-op rows.
    """
    from .models import MovementType
    from .services import apply_stock_movement
    from .stocktake import StockTakeStatus

    if stocktake.status != StockTakeStatus.DRAFT:
        raise ValidationError(_("This stocktake has already been closed."))

    lines = list(stocktake.lines.select_related("medicine"))
    counted = [line for line in lines if line.counted_quantity is not None]
    if not counted:
        raise ValidationError(
            _("Nothing has been counted yet, so there is nothing to post.")
        )

    applied, net, value = 0, 0, Decimal("0.00")
    for line in counted:
        variance = line.variance
        if not variance:
            continue
        apply_stock_movement(
            medicine_id=line.medicine_id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=line.counted_quantity,   # absolute counted total
            branch=stocktake.branch,
            reason=_("Stocktake %(ref)s: counted %(counted)s, expected %(expected)s. "
                     "%(note)s") % {
                "ref": stocktake.reference, "counted": line.counted_quantity,
                "expected": line.expected_quantity, "note": line.note or ""},
            user=user,
        )
        applied += 1
        net += variance
        value += line.variance_value

    stocktake.status = StockTakeStatus.POSTED
    stocktake.posted_by = user
    stocktake.posted_at = timezone.now()
    stocktake.save(update_fields=["status", "posted_by", "posted_at"])

    return {
        "lines_counted": len(counted),
        "lines_uncounted": len(lines) - len(counted),
        "adjustments": applied,
        "net_units": net,
        "value": value.quantize(Decimal("0.01")),
    }


def cancel_stocktake(*, stocktake, user=None):
    """Abandons a count without touching stock."""
    from .stocktake import StockTakeStatus

    if stocktake.status != StockTakeStatus.DRAFT:
        raise ValidationError(_("Only a stocktake in progress can be cancelled."))
    stocktake.status = StockTakeStatus.CANCELLED
    stocktake.posted_by = user
    stocktake.posted_at = timezone.now()
    stocktake.save(update_fields=["status", "posted_by", "posted_at"])
    return stocktake


# ---------------------------------------------------------------------------
# Reorder suggestions
# ---------------------------------------------------------------------------
def sales_velocity(branch=None, days=VELOCITY_WINDOW_DAYS):
    """Units sold per day per product over the window.

    Voided sales are excluded — they did not represent demand.
    """
    from apps.sales.models import SaleItem, SaleStatus

    since = timezone.now() - timezone.timedelta(days=days)
    items = SaleItem.objects.filter(
        sale__status=SaleStatus.COMPLETED, sale__created_at__gte=since
    )
    if branch is not None:
        items = items.filter(sale__branch=branch)

    rows = items.values("medicine_id").annotate(units=Sum("quantity"))
    return {r["medicine_id"]: (r["units"] or 0) / days for r in rows}


def reorder_suggestions(branch=None, target_days=TARGET_DAYS_OF_COVER,
                        include_healthy=False):
    """What to order, how much, and why.

    Returns a list of dicts sorted by urgency (fewest days of cover first).
    Set `include_healthy` to see every product rather than only those at or
    below their reorder level — useful when planning a large order.
    """
    from apps.branches.models import BranchStock

    velocity = sales_velocity(branch)
    rows = BranchStock.objects.filter(medicine__is_active=True).select_related(
        "medicine", "medicine__supplier", "branch"
    )
    if branch is not None:
        rows = rows.filter(branch=branch)

    suggestions = []
    for row in rows:
        per_day = velocity.get(row.medicine_id, 0)
        below_level = row.quantity <= row.reorder_level
        if not below_level and not include_healthy:
            continue

        if per_day > 0:
            days_left = row.quantity / per_day
            # Order enough to reach the target cover, rounded up.
            target_units = int(per_day * target_days + 0.999)
            suggested = max(target_units - row.quantity, 0)
        else:
            # No recent sales: no basis for a velocity figure, so top up to
            # twice the reorder level as a holding position rather than
            # suggesting nothing for something that has run out.
            days_left = None
            suggested = max(row.reorder_level * 2 - row.quantity, 0)

        if suggested <= 0 and not include_healthy:
            continue

        cost = row.medicine.purchase_price or Decimal("0.00")
        suggestions.append({
            "branch": row.branch,
            "medicine": row.medicine,
            "on_hand": row.quantity,
            "reorder_level": row.reorder_level,
            "per_day": round(per_day, 2),
            "days_of_cover": round(days_left, 1) if days_left is not None else None,
            "suggested_quantity": suggested,
            "estimated_cost": (cost * suggested).quantize(Decimal("0.01")),
            "supplier": row.medicine.supplier,
            "is_out": row.quantity == 0,
            "below_level": below_level,
        })

    # Out of stock first, then fewest days of cover. `None` (no sales history)
    # sorts last: a product nobody buys is the least urgent thing to reorder.
    suggestions.sort(key=lambda s: (
        not s["is_out"],
        s["days_of_cover"] if s["days_of_cover"] is not None else 10_000,
    ))
    return suggestions


def stock_aging(branch=None):
    """Stock on hand bucketed by how long until it expires, with value.

    Different from the expiry report: this values what is at risk using
    actual batch costs rather than the product's headline cost, so the figure
    reflects what the pharmacy would really lose.
    """
    from .batches import StockBatch

    today = timezone.localdate()
    buckets = [
        (_("Expired"), None, 0),
        (_("0–30 days"), 0, 30),
        (_("31–90 days"), 30, 90),
        (_("91–180 days"), 90, 180),
        (_("Over 180 days"), 180, None),
        (_("No expiry"), "none", "none"),
    ]

    batches = StockBatch.objects.filter(quantity_remaining__gt=0).select_related("medicine")
    if branch is not None:
        batches = batches.filter(branch=branch)

    result = []
    for label, low, high in buckets:
        units, value = 0, Decimal("0.00")
        for batch in batches:
            if low == "none":
                match = batch.expiry_date is None
            elif batch.expiry_date is None:
                match = False
            else:
                days = (batch.expiry_date - today).days
                if low is None:
                    match = days < 0
                elif high is None:
                    match = days > low
                else:
                    match = low < days <= high if low else 0 <= days <= high
            if match:
                units += batch.quantity_remaining
                value += batch.unit_cost * batch.quantity_remaining
        result.append({
            "label": label, "units": units,
            "value": value.quantize(Decimal("0.01")),
        })
    return result
