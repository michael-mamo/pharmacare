"""
Business logic for completing and voiding a sale.

Kept out of the view so the POS endpoint stays thin and the rules are
testable in isolation. Both functions are atomic and lock the Medicine
rows they touch, so concurrent cashiers cannot oversell the last unit.
"""
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.inventory.allocation import (
    consume_stock,
    ensure_opening_batch,
    return_stock,
)


def branch_available(medicine, branch):
    """Units of `medicine` on hand at `branch`.

    Falls back to the pharmacy-wide figure only when there is no branch at
    all, so a single-branch install behaves exactly as before.
    """
    if branch is None:
        return medicine.quantity or 0
    from apps.branches.models import BranchStock

    row = BranchStock.objects.filter(branch=branch, medicine=medicine).first()
    return row.quantity if row else 0
from apps.medicine.models import Medicine

from .models import Sale, SaleItem, SaleStatus

logger = logging.getLogger(__name__)

# One loyalty point per this many currency units spent. Lives here rather
# than hard-coded in a view so the Phase 6 Settings module can lift it into
# the database without touching sale logic.
LOYALTY_POINTS_PER_CURRENCY_UNIT = Decimal("100")

#: Fallback threshold for the large-sale alert, used when no PharmacySettings
#: row has been saved yet.
LARGE_SALE_THRESHOLD_FALLBACK = Decimal("1000.00")


@transaction.atomic
def complete_sale(*, cart, customer=None, payment_method, amount_paid, user,
                  branch=None, notes=""):
    """Creates a Sale from `cart` and decrements stock.

    `cart` is a list of dicts: {medicine_id, quantity, discount_percent}.
    Unit price and VAT are taken from the Medicine at sale time and
    snapshotted onto each SaleItem — never re-read later.

    Raises ValidationError (not a 500) for an empty cart or insufficient
    stock, so the POS can surface it as a normal error message.
    """
    if not cart:
        raise ValidationError(_("Cannot complete a sale with an empty cart."))

    medicine_ids = [row["medicine_id"] for row in cart]
    # Lock every medicine in the cart up front, ordered by pk to avoid
    # deadlocking against another concurrent sale touching the same rows.
    medicines = {
        m.pk: m
        for m in Medicine.objects.select_for_update().filter(pk__in=medicine_ids).order_by("pk")
    }

    # Make sure every product has batch coverage at THIS branch before
    # validating, so stock that predates batch tracking doesn't fail a sale.
    for medicine in medicines.values():
        ensure_opening_batch(medicine, branch=branch)

    # Validate the whole cart before writing anything.
    #
    # Quantities are aggregated PER MEDICINE first. Checking each cart line
    # independently was a real oversell bug: two lines of 490 against 500
    # stock both passed (490 <= 500 each) even though the total was 980. The
    # batch layer caught it and the transaction rolled back, but the error the
    # cashier saw was confusing and the check belongs here.
    requested = {}
    for row in cart:
        if not isinstance(row.get("quantity"), int) or row["quantity"] < 1:
            raise ValidationError(_("Quantity must be a whole number of at least 1."))
        requested[row["medicine_id"]] = requested.get(row["medicine_id"], 0) + row["quantity"]

    for medicine_id, total_wanted in requested.items():
        medicine = medicines.get(medicine_id)
        if medicine is None:
            raise ValidationError(_("One of the selected products no longer exists."))
        # Check the SELLING BRANCH's stock, not the pharmacy-wide total.
        # Using Medicine.quantity here would let a branch sell stock that
        # physically sits in another branch.
        available = branch_available(medicine, branch)
        if total_wanted > available:
            raise ValidationError(
                _('Not enough stock for "%(name)s"%(where)s: %(want)s requested, '
                  "%(have)s available.")
                % {"name": medicine.name,
                   "where": f" at {branch.name}" if branch else "",
                   "want": total_wanted, "have": available}
            )

    sale = Sale.objects.create(
        branch=branch,
        customer=customer,
        payment_method=payment_method,
        amount_paid=amount_paid or Decimal("0.00"),
        served_by=user,
        notes=notes,
    )

    for row in cart:
        medicine = medicines[row["medicine_id"]]
        item = SaleItem.objects.create(
            sale=sale,
            medicine=medicine,
            medicine_name=medicine.name,
            quantity=row["quantity"],
            unit_price=medicine.selling_price,
            discount_percent=row.get("discount_percent") or medicine.discount_percent,
            tax_percent=medicine.tax_percent,
        )
        # Draw the units from real batches, FEFO, and record what they cost.
        # consume_stock() decrements Medicine.quantity itself, so we must not
        # also adjust it here or the stock would be double-counted.
        ensure_opening_batch(medicine, branch=branch)
        allocations = consume_stock(
            medicine=medicine, quantity=row["quantity"], branch=branch, sale_item=item,
            exclude_expired=True,
        )
        total_cost = sum((qty * cost for _b, qty, cost in allocations), Decimal("0.00"))
        item.unit_cost = (total_cost / row["quantity"]).quantize(Decimal("0.01"))
        item.save(update_fields=["unit_cost"])

    # Award loyalty points to a named customer (walk-ins have none). The
    # rate comes from Settings (Phase 6) with the module constant as a
    # fallback for a deployment that hasn't saved settings yet.
    if customer:
        rate = LOYALTY_POINTS_PER_CURRENCY_UNIT
        threshold = LARGE_SALE_THRESHOLD_FALLBACK
        conf = _pharmacy_settings()
        if conf is not None:
            rate = Decimal(conf.loyalty_points_per_unit or rate)
        points = int(sale.grand_total / rate) if rate else 0
        if points > 0:
            customer.loyalty_points += points
            customer.save(update_fields=["loyalty_points"])

    # Large-sale alert (Phase 6). Never let a notification failure undo a
    # completed sale.
    try:
        threshold = LARGE_SALE_THRESHOLD_FALLBACK
        conf = _pharmacy_settings()
        if conf is not None and conf.large_sale_threshold is not None:
            threshold = conf.large_sale_threshold
        if sale.grand_total >= threshold:
            from apps.notifications.services import notify_large_sale

            notify_large_sale(sale)
    except Exception:
        logger.exception("Could not create large-sale notification")

    return sale


def _pharmacy_settings():
    try:
        from apps.settings_app.models import PharmacySettings

        return PharmacySettings.load()
    except Exception:
        return None


@transaction.atomic
def void_sale(*, sale, user, reason=""):
    """Voids a completed sale and returns its stock. Idempotent-safe: a
    sale that is already voided raises rather than double-returning stock."""
    if sale.status == SaleStatus.VOIDED:
        raise ValidationError(_("This sale has already been voided."))

    for item in sale.items.select_related("medicine"):
        # Return units to the batches they came from, so the cost of those
        # units is preserved rather than being averaged into new stock.
        returned = return_stock(sale_item=item)
        if returned < item.quantity:
            # Legacy sale with no batch allocations (pre-batch data): fall
            # back to a plain quantity restore so stock isn't lost.
            Medicine.objects.filter(pk=item.medicine_id).update(
                quantity=F("quantity") + (item.quantity - returned)
            )

    sale.status = SaleStatus.VOIDED
    sale.voided_by = user
    sale.voided_at = timezone.now()
    sale.void_reason = reason
    sale.save(update_fields=["status", "voided_by", "voided_at", "void_reason"])
    return sale
