"""
Registering a catalogue product as a pharmacy stock item.

The catalogue holds identity; `Medicine` holds the commercial and stock
detail. `register_product` bridges the two: it copies the standardised
fields across, leaves prices for the pharmacy to set, and records the link so
group reporting can group by catalogue record rather than by typed name.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _


@transaction.atomic
def register_product(*, catalogue_product, category, branch=None, supplier=None,
                     purchase_price=None, selling_price=None, quantity=0,
                     reorder_level=None, expiry_date=None, batch_number="",
                     tax_percent=None, user=None):
    """Creates a `Medicine` from a catalogue record.

    Refuses to create a second stock item for the same catalogue record,
    because two rows for one identity is precisely the duplication the
    catalogue exists to prevent — the caller is told which record already
    exists so they can edit it instead.
    """
    from apps.medicine.models import Medicine

    existing = Medicine.objects.filter(catalogue_product=catalogue_product).first()
    if existing:
        raise ValidationError(
            _('"%(name)s" is already registered as %(code)s. Edit that product '
              "instead of registering it twice.")
            % {"name": catalogue_product.display_name, "code": existing.code}
        )

    if catalogue_product.product_type != "DEVICE" and expiry_date is None:
        # Mirrors Medicine.clean(), but caught here so the message names the
        # catalogue product rather than a field on a half-built object.
        raise ValidationError(
            _('An expiry date is required for "%(name)s".')
            % {"name": catalogue_product.display_name}
        )

    medicine = Medicine(
        catalogue_product=catalogue_product,
        product_type=catalogue_product.product_type,
        name=catalogue_product.short_name,
        generic_name=catalogue_product.generic_name,
        brand=catalogue_product.brand_name,
        category=category,
        supplier=supplier,
        unit=catalogue_product.default_unit,
        # NULL, not "": Medicine.barcode is unique with null=True, so blanks
        # must be NULL. An empty string would collide with the next product
        # that also has no barcode.
        barcode=catalogue_product.barcode or None,
        batch_number=batch_number,
        expiry_date=expiry_date,
        purchase_price=purchase_price if purchase_price is not None else Decimal("0.00"),
        selling_price=selling_price if selling_price is not None else Decimal("0.00"),
        quantity=quantity or 0,
        reorder_level=reorder_level if reorder_level is not None else 10,
        # The catalogue's legal class decides this, not the person registering,
        # so a prescription-only medicine cannot be registered as over-counter.
        requires_prescription=catalogue_product.requires_prescription,
        description=catalogue_product.notes or "",
    )
    if tax_percent is not None:
        medicine.tax_percent = tax_percent
    medicine.full_clean(exclude=["code"])
    medicine.save()
    return medicine


def unregistered_products(search="", category=None, limit=None):
    """Catalogue products this pharmacy has not registered yet."""
    from apps.catalogue.models import CatalogueProduct

    qs = CatalogueProduct.objects.filter(
        is_active=True, medicines__isnull=True
    ).select_related("category")
    if search:
        qs = (qs.filter(generic_name__icontains=search)
              | qs.filter(brand_name__icontains=search)
              | qs.filter(atc_code__icontains=search)).filter(
                  is_active=True, medicines__isnull=True)
    if category is not None:
        qs = qs.filter(category=category)
    qs = qs.distinct().order_by("generic_name", "strength")
    return qs[:limit] if limit else qs


def catalogue_coverage():
    """How much of the catalogue this pharmacy stocks, and how much of its
    stock is standardised. The second number is the useful one: unlinked
    products are the ones that will not roll up in group reporting."""
    from apps.catalogue.models import CatalogueProduct
    from apps.medicine.models import Medicine

    total_catalogue = CatalogueProduct.objects.filter(is_active=True).count()
    registered = Medicine.objects.filter(catalogue_product__isnull=False).count()
    unlinked = Medicine.objects.filter(catalogue_product__isnull=True).count()
    stock_items = registered + unlinked
    return {
        "catalogue_size": total_catalogue,
        "registered": registered,
        "unlinked": unlinked,
        "stock_items": stock_items,
        "linked_percent": int(registered / stock_items * 100) if stock_items else 0,
        "coverage_percent": int(registered / total_catalogue * 100) if total_catalogue else 0,
    }
