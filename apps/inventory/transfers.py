"""
Moving stock between branches.

A transfer is two half-movements that must succeed or fail together: units
leave the source branch and arrive at the destination. Doing it in one atomic
function is the only way to guarantee the pharmacy never loses or duplicates
stock in transit.

**Cost is carried across.** The units arrive at the destination at the exact
cost they left at, batch by batch. The alternative — receiving them at the
destination's current average cost — would quietly manufacture or destroy
profit every time stock moved between branches, and would make each branch's
margin depend on transfer history rather than on trading.

**Expiry is carried across too**, so the destination continues to dispense
first-expired-first-out correctly rather than treating transferred stock as
newly arrived.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from .allocation import available_batches
from .batches import StockBatch


@transaction.atomic
def transfer_stock(*, medicine, quantity, source_branch, destination_branch,
                   user=None, reason=""):
    """Moves `quantity` units of `medicine` from one branch to another.

    Returns the list of StockBatch rows created at the destination.
    """
    from apps.branches.models import BranchStock

    if source_branch is None or destination_branch is None:
        raise ValidationError(_("Both a source and a destination branch are required."))
    if source_branch.pk == destination_branch.pk:
        raise ValidationError(_("The source and destination branch must be different."))
    if not destination_branch.is_active:
        raise ValidationError(
            _("%(branch)s is inactive and cannot receive stock.")
            % {"branch": destination_branch.name}
        )
    if quantity is None or quantity < 1:
        raise ValidationError(_("Transfer quantity must be at least 1."))

    # Validate against the source branch's own batches before moving anything.
    batches = list(available_batches(medicine, branch=source_branch))
    total_available = sum(b.quantity_remaining for b in batches)
    if total_available < quantity:
        raise ValidationError(
            _('Not enough stock for "%(name)s" at %(branch)s: %(want)s requested, '
              "%(have)s available.")
            % {"name": medicine.name, "branch": source_branch.name,
               "want": quantity, "have": total_available}
        )

    remaining = quantity
    created = []
    note = reason or _("Transferred from %(branch)s") % {"branch": source_branch.name}

    # Send soonest-expiring first, matching how the source would have
    # dispensed them anyway.
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity_remaining, remaining)
        batch.quantity_remaining -= take
        batch.save(update_fields=["quantity_remaining"])
        remaining -= take

        created.append(StockBatch.objects.create(
            branch=destination_branch,
            medicine=medicine,
            batch_number=batch.batch_number,
            unit_cost=batch.unit_cost,          # cost travels with the goods
            selling_price=batch.selling_price,
            quantity_received=take,
            quantity_remaining=take,
            expiry_date=batch.expiry_date,      # so FEFO still works there
            source="TRANSFER",
            note=str(note)[:200],
        ))

    # Update both branches' stock levels through the central funnel, so each
    # side gets its own ledger entry and the pair can be reconciled later.
    from .allocation import _adjust_branch_stock
    from .stocktake import LedgerSource

    avg_cost = transfer_value(created) / quantity if quantity else None
    _adjust_branch_stock(
        source_branch, medicine, -quantity,
        source=LedgerSource.TRANSFER_OUT,
        reference=f"→ {destination_branch.code}",
        unit_cost=avg_cost, note=str(note)[:255], user=user,
    )
    _adjust_branch_stock(
        destination_branch, medicine, +quantity,
        source=LedgerSource.TRANSFER_IN,
        reference=f"← {source_branch.code}",
        unit_cost=avg_cost, note=str(note)[:255], user=user,
    )

    return created


def transfer_value(batches):
    """Total cost value of the batches created by a transfer — useful for the
    movement record and for inter-branch reconciliation."""
    return sum(
        (b.unit_cost * b.quantity_received for b in batches), Decimal("0.00")
    ).quantize(Decimal("0.01"))
