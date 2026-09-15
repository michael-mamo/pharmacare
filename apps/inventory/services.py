"""
Business logic for recording a stock movement. Kept out of the view/form
so it can be reused (e.g. from a future API endpoint) and unit-tested in
isolation. Uses select_for_update to avoid a race condition if two staff
members adjust the same medicine's stock at the same moment.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from apps.medicine.models import Medicine

from .models import MovementType, StockMovement


@transaction.atomic
def apply_stock_movement(*, medicine_id, movement_type, quantity, branch=None,
                         destination_branch=None, destination="", reason="", user=None):
    """Applies a stock movement at one branch and records it.

    Raises ValidationError for invalid input (Stock Out exceeding stock, a
    transfer without a destination, and so on) so the view shows a normal
    form error rather than a 500.

    Branch behaviour
    ----------------
    * All four types act on **this branch's** stock level, never the
      pharmacy-wide total.
    * STOCK_IN and ADJUSTMENT keep the batch ledger in step: adding units
      creates a batch at the product's current cost (there is no supplier
      invoice to cost them against), and removing units draws down batches
      FEFO, exactly as a sale would. Without this, BranchStock and the batch
      records would drift and profit figures would decay.
    * TRANSFER with a `destination_branch` performs a real inter-branch move
      via `transfers.transfer_stock`, carrying cost and expiry across. The
      legacy free-text `destination` still works for stock genuinely leaving
      the pharmacy.
    """
    from apps.branches.models import BranchStock

    from .allocation import _resolve_branch, consume_stock, ensure_opening_batch, receive_batch
    from .transfers import transfer_stock

    medicine = Medicine.objects.select_for_update().get(pk=medicine_id)
    branch = _resolve_branch(branch)
    if branch is None:
        raise ValidationError(_("An active branch is required to move stock."))

    ensure_opening_batch(medicine, branch=branch)
    stock_row = BranchStock.get_or_create_for(branch, medicine)
    quantity_before = stock_row.quantity

    if movement_type == MovementType.STOCK_IN:
        if quantity < 1:
            raise ValidationError(_("Quantity must be at least 1."))
        # No supplier invoice, so cost these at the product's current price
        # and label the batch so it is recognisable in the batch list.
        receive_batch(
            branch=branch, medicine=medicine, quantity=quantity,
            unit_cost=medicine.purchase_price or 0, source="ADJUSTMENT",
            ledger_source="STOCK_IN", reference=str(reason or "")[:60],
            note=str(reason or _("Stock In"))[:200], user=user,
        )
        quantity_after = quantity_before + quantity

    elif movement_type == MovementType.STOCK_OUT:
        if quantity > quantity_before:
            raise ValidationError(
                _("Cannot remove %(qty)s units — only %(available)s in stock at "
                  "%(branch)s.")
                % {"qty": quantity, "available": quantity_before, "branch": branch.name}
            )
        consume_stock(medicine=medicine, quantity=quantity, branch=branch,
                      ledger_source="STOCK_OUT", note=str(reason or "")[:255],
                      user=user)
        quantity_after = quantity_before - quantity

    elif movement_type == MovementType.ADJUSTMENT:
        # `quantity` here is the new counted total, not a delta.
        delta = quantity - quantity_before
        if delta > 0:
            receive_batch(
                branch=branch, medicine=medicine, quantity=delta,
                unit_cost=medicine.purchase_price or 0, source="ADJUSTMENT",
                ledger_source="ADJUSTMENT", note=str(reason or _("Stock count adjustment"))[:200],
                user=user,
            )
        elif delta < 0:
            consume_stock(medicine=medicine, quantity=-delta, branch=branch,
                          allow_partial=True, ledger_source="ADJUSTMENT",
                          note=str(reason or _("Stock count adjustment"))[:255],
                          user=user)
        quantity_after = quantity

    elif movement_type == MovementType.TRANSFER:
        if destination_branch is None and not destination:
            raise ValidationError(
                _("Choose a destination branch, or type an external destination.")
            )
        if quantity > quantity_before:
            raise ValidationError(
                _("Cannot transfer %(qty)s units — only %(available)s in stock at "
                  "%(branch)s.")
                % {"qty": quantity, "available": quantity_before, "branch": branch.name}
            )
        if destination_branch is not None:
            # Real branch-to-branch move: both sides updated atomically, with
            # cost and expiry preserved.
            transfer_stock(
                medicine=medicine, quantity=quantity, source_branch=branch,
                destination_branch=destination_branch, user=user, reason=reason,
            )
        else:
            consume_stock(medicine=medicine, quantity=quantity, branch=branch)
        quantity_after = quantity_before - quantity

    else:
        raise ValidationError(_("Unknown movement type."))

    # consume_stock / receive_batch already moved BranchStock; re-read rather
    # than assuming, so the recorded before/after figures are the truth.
    stock_row.refresh_from_db()

    return StockMovement.objects.create(
        branch=branch,
        medicine=medicine,
        movement_type=movement_type,
        quantity=quantity,
        quantity_before=quantity_before,
        quantity_after=stock_row.quantity,
        destination_branch=destination_branch,
        destination=destination or (destination_branch.name if destination_branch else ""),
        reason=reason,
        performed_by=user,
    )
