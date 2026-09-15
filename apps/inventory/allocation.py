"""
Batch allocation engine.

All stock movement flows through these three functions so `Medicine.quantity`
and the sum of `StockBatch.quantity_remaining` can never drift apart:

  receive_batch()  — a purchase, opening balance, or Stock In
  consume_stock()  — a sale, Stock Out, or Transfer  (FEFO)
  return_stock()   — voiding a sale, or reversing a purchase

Callers must already hold a row lock on the Medicine (see
`apps.sales.services.complete_sale`), which is why these helpers don't open
their own transaction — they're building blocks, not entry points.
"""
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from .batches import SaleItemCost, StockBatch

logger = logging.getLogger(__name__)

#: Maps a StockBatch.source to the ledger cause, so the ledger explains *why*
#: stock arrived rather than just that it did.
_LEDGER_BY_BATCH_SOURCE = {
    "PURCHASE": "PURCHASE",
    "TRANSFER": "TRANSFER_IN",
    "OPENING": "OPENING",
    "RETURN": "RETURN",
    "ADJUSTMENT": "ADJUSTMENT",
}


def _resolve_branch(branch):
    """Falls back to the main branch when a caller passes nothing.

    Keeps pre-branch call sites working and guarantees stock is always
    attributed somewhere rather than floating unassigned.
    """
    if branch is not None:
        return branch
    from apps.branches.models import Branch

    return (
        Branch.objects.filter(is_main=True, is_active=True).first()
        or Branch.objects.filter(is_active=True).first()
    )


def _adjust_branch_stock(branch, medicine, delta, *, source=None, reference="",
                         unit_cost=None, note="", user=None):
    """Applies `delta` to this branch's stock level and writes the ledger.

    All stock changes funnel through here, which is why the ledger write lives
    here too: a new caller gets complete audit history for free and cannot
    forget to log. BranchStock, the cached `Medicine.quantity` rollup and the
    ledger therefore cannot drift apart.
    """
    if branch is None or not delta:
        return
    from apps.branches.models import BranchStock

    row = BranchStock.get_or_create_for(branch, medicine)
    before = row.quantity or 0
    row.quantity = max(before + delta, 0)
    row.save(update_fields=["quantity", "updated_at"])  # syncs Medicine.quantity

    _write_ledger(
        branch=branch, medicine=medicine, delta=row.quantity - before,
        before=before, after=row.quantity, source=source, reference=reference,
        unit_cost=unit_cost, note=note, user=user,
    )


def _write_ledger(*, branch, medicine, delta, before, after, source=None,
                  reference="", unit_cost=None, note="", user=None):
    """Appends one ledger row. Never raises: an audit-trail failure must not
    roll back the stock movement it was describing."""
    from .stocktake import LedgerSource, StockLedger

    if not delta:
        return
    try:
        if user is None:
            from apps.accounts.middleware import get_current_user

            candidate = get_current_user()
            user = candidate if getattr(candidate, "is_authenticated", False) else None
        StockLedger.objects.create(
            branch=branch, medicine=medicine,
            source=source or LedgerSource.OTHER,
            quantity_change=delta, balance_before=before, balance_after=after,
            unit_cost=unit_cost, reference=str(reference or "")[:60],
            note=str(note or "")[:255], performed_by=user,
        )
    except Exception:  # pragma: no cover
        logger.warning("Could not write stock ledger entry", exc_info=True)


def receive_batch(*, medicine, quantity, unit_cost, branch=None, expiry_date=None,
                  batch_number="", purchase_item=None, source="PURCHASE",
                  selling_price=None, note="", ledger_source=None, reference="",
                  user=None):
    """Adds a batch at `branch` and increases that branch's stock level.

    `branch` is keyword-only and defaults to the main branch, so callers
    written before multi-branch support keep working instead of silently
    creating unattributed stock.
    """
    if quantity <= 0:
        raise ValidationError(_("Quantity received must be greater than zero."))
    branch = _resolve_branch(branch)

    batch = StockBatch.objects.create(
        branch=branch,
        medicine=medicine,
        purchase_item=purchase_item,
        batch_number=batch_number or (medicine.batch_number or ""),
        unit_cost=Decimal(str(unit_cost)),
        selling_price=selling_price,
        quantity_received=quantity,
        quantity_remaining=quantity,
        expiry_date=expiry_date or medicine.expiry_date,
        received_at=timezone.now(),
        source=source,
        note=note,
    )
    from .stocktake import LedgerSource

    _adjust_branch_stock(
        branch, medicine, +quantity,
        source=ledger_source or _LEDGER_BY_BATCH_SOURCE.get(source, LedgerSource.STOCK_IN),
        reference=reference or (purchase_item.purchase.purchase_number
                               if purchase_item and purchase_item.purchase_id else ""),
        unit_cost=Decimal(str(unit_cost)), note=note, user=user,
    )
    return batch


def available_batches(medicine, branch=None, exclude_expired=False):
    """Batches with stock left at this branch, in FEFO order.

    Filtering by branch is essential, not cosmetic: without it a sale in one
    branch would draw down another branch's batches and report that branch's
    costs.

    `exclude_expired` leaves already-expired batches out of the result
    entirely. Default is False so Stock Out, Transfer and reconciliation can
    still move or write off expired stock — the batch has to go *somewhere*.
    Sales pass True: selling expired medication isn't a stock-level nuance,
    it's not allowed, and FEFO ordering alone doesn't protect against it —
    the earliest-expiry batch is picked *first*, so an expired batch would
    otherwise be the one most likely to get sold.
    """
    qs = StockBatch.objects.filter(medicine=medicine, quantity_remaining__gt=0)
    if branch is not None:
        qs = qs.filter(branch=branch)
    if exclude_expired:
        qs = qs.filter(expiry_date__gte=timezone.localdate())
    return qs.order_by("expiry_date", "received_at", "pk")


def consume_stock(*, medicine, quantity, branch=None, sale_item=None,
                  allow_partial=False, ledger_source=None, reference="",
                  note="", user=None, exclude_expired=False):
    """Draws `quantity` units from batches FEFO.

    Returns a list of (batch, qty_taken, unit_cost) tuples. When `sale_item`
    is given, writes a SaleItemCost row per batch so the sale's true cost of
    goods is permanently recorded.

    Raises ValidationError if there isn't enough batch stock, unless
    `allow_partial` is set — used only by the reconciliation path for
    pre-batch legacy stock. Pass `exclude_expired=True` for anything that
    hands stock to a customer (see `available_batches`); leave it False for
    internal movements that need to touch expired batches too.
    """
    if quantity <= 0:
        raise ValidationError(_("Quantity must be greater than zero."))
    branch = _resolve_branch(branch)

    batches = list(available_batches(medicine, branch=branch, exclude_expired=exclude_expired))
    total_available = sum(b.quantity_remaining for b in batches)

    if total_available < quantity and not allow_partial:
        if exclude_expired:
            all_batches = list(available_batches(medicine, branch=branch))
            total_all = sum(b.quantity_remaining for b in all_batches)
            if total_all >= quantity:
                # There's enough stock on the shelf, but some or all of it
                # has expired — say that plainly rather than reporting a
                # generic shortfall that sends someone looking for a
                # delivery that was never missing.
                raise ValidationError(
                    _('"%(name)s" at %(branch)s has expired stock only for the '
                      "requested quantity (%(want)s wanted, %(have)s in date). "
                      "Write the expired batch off via a Stock Adjustment before "
                      "it can be sold.")
                    % {"name": medicine.name, "branch": branch.name if branch else "-",
                       "want": quantity, "have": total_available}
                )
        raise ValidationError(
            _('Not enough stock for "%(name)s" at %(branch)s: %(want)s requested, '
              "%(have)s available.")
            % {"name": medicine.name, "branch": branch.name if branch else "-",
               "want": quantity, "have": total_available}
        )

    remaining = min(quantity, total_available) if allow_partial else quantity
    allocations = []

    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity_remaining, remaining)
        batch.quantity_remaining -= take
        batch.save(update_fields=["quantity_remaining"])
        remaining -= take
        allocations.append((batch, take, batch.unit_cost))

        if sale_item is not None:
            SaleItemCost.objects.create(
                sale_item=sale_item, batch=batch, quantity=take,
                unit_cost=batch.unit_cost,
            )

    from .stocktake import LedgerSource

    taken = quantity - remaining
    # Weighted cost of what actually left, so the ledger carries real value.
    cost = None
    if taken and allocations:
        total = sum((qty * unit for _b, qty, unit in allocations), Decimal("0.00"))
        cost = (total / taken).quantize(Decimal("0.01"))
    if sale_item is not None and not reference:
        reference = getattr(sale_item.sale, "invoice_number", "")
    _adjust_branch_stock(
        branch, medicine, -taken,
        source=ledger_source or (LedgerSource.SALE if sale_item is not None
                                 else LedgerSource.STOCK_OUT),
        reference=reference, unit_cost=cost, note=note, user=user,
    )
    return allocations


def return_stock(*, sale_item):
    """Returns a sale line's units to the batches they came from.

    Used when voiding a sale. Restoring to the *original* batches (rather
    than creating a new one) keeps costing honest — the units go back at the
    cost they left at, so a void followed by a re-sale reports the same
    profit as the original sale would have.
    """
    medicine = sale_item.medicine
    # Return to the branch that sold it, which is the branch its batches
    # belong to — not whichever branch the person voiding happens to be in.
    branch = _resolve_branch(getattr(sale_item.sale, "branch", None))
    returned = 0
    for allocation in sale_item.cost_allocations.select_related("batch"):
        if allocation.batch is not None:
            batch = allocation.batch
            batch.quantity_remaining += allocation.quantity
            batch.save(update_fields=["quantity_remaining"])
            branch = batch.branch or branch
        else:
            # The batch row is gone (rare). Recreate one at the recorded cost
            # so the stock isn't lost and costing stays accurate.
            StockBatch.objects.create(
                branch=branch,
                medicine=medicine,
                batch_number=_("returned"),
                unit_cost=allocation.unit_cost,
                quantity_received=allocation.quantity,
                quantity_remaining=allocation.quantity,
                expiry_date=medicine.expiry_date,
                source="RETURN",
                note=_("Recreated when voiding a sale."),
            )
        returned += allocation.quantity

    if returned:
        from .stocktake import LedgerSource

        _adjust_branch_stock(
            branch, medicine, +returned, source=LedgerSource.SALE_VOID,
            reference=getattr(sale_item.sale, "invoice_number", ""),
            unit_cost=sale_item.unit_cost or None,
            note=str(_("Returned to stock when the sale was voided")),
        )
    return returned


def weighted_average_cost(medicine, branch=None):
    """Current average cost of remaining stock — the figure to use for
    valuing inventory on hand (as opposed to cost of goods sold, which comes
    from the batches actually consumed)."""
    batches = available_batches(medicine, branch=branch)
    total_qty = sum(b.quantity_remaining for b in batches)
    if not total_qty:
        return medicine.purchase_price or Decimal("0.00")
    total_value = sum(b.unit_cost * b.quantity_remaining for b in batches)
    return (total_value / total_qty).quantize(Decimal("0.01"))


def stock_value(medicine, branch=None):
    """Value of stock on hand at actual batch costs, optionally per branch."""
    return sum(
        (b.unit_cost * b.quantity_remaining
         for b in available_batches(medicine, branch=branch)),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))


def batch_quantity(medicine, branch=None):
    qs = StockBatch.objects.filter(medicine=medicine)
    if branch is not None:
        qs = qs.filter(branch=branch)
    return qs.aggregate(total=Sum("quantity_remaining"))["total"] or 0


def verify_consistency(medicine, branch=None):
    """Returns (recorded_quantity, batch_total, is_consistent).

    With a branch given, compares that branch's BranchStock against its own
    batches. Without one, compares the cached pharmacy-wide total.
    """
    batch_total = batch_quantity(medicine, branch=branch)
    if branch is not None:
        from apps.branches.models import BranchStock

        row = BranchStock.objects.filter(branch=branch, medicine=medicine).first()
        recorded = row.quantity if row else 0
        return recorded, batch_total, recorded == batch_total
    return medicine.quantity, batch_total, medicine.quantity == batch_total


def ensure_opening_batch(medicine, branch=None):
    """Creates an OPENING batch for stock that predates batch tracking.

    Needed for two cases: medicines that existed before this feature, and
    medicines whose quantity was set directly (e.g. on the create form)
    rather than through a purchase. Without it, a sale would fail with
    "not enough batch stock" despite Medicine.quantity looking healthy.
    """
    branch = _resolve_branch(branch)
    from apps.branches.models import BranchStock

    row = BranchStock.objects.filter(branch=branch, medicine=medicine).first()
    recorded = row.quantity if row else 0
    shortfall = recorded - batch_quantity(medicine, branch=branch)
    if shortfall <= 0:
        return None
    return StockBatch.objects.create(
        branch=branch,
        medicine=medicine,
        batch_number=medicine.batch_number or "",
        unit_cost=medicine.purchase_price or Decimal("0.00"),
        selling_price=medicine.selling_price,
        quantity_received=shortfall,
        quantity_remaining=shortfall,
        expiry_date=medicine.expiry_date,
        source="OPENING",
        note=_("Opening balance for stock recorded before batch tracking."),
    )
