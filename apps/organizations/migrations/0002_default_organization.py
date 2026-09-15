"""
Moves an existing single-pharmacy installation onto the tenancy model.

Anyone upgrading already has branches, staff, products, customers, suppliers,
sales and purchases that predate organizations. Leaving those rows unowned
would make every scoped query return nothing the moment strict mode is on —
the system would appear empty.

So this creates one organization from the existing pharmacy settings (falling
back to a sensible default) and assigns everything to it. Running on a fresh
database is equally safe: it produces the single organization a new install
needs anyway.

Platform staff are deliberately left with no organization. That null is what
distinguishes someone who runs the platform from someone who works for a
pharmacy, so filling it in would silently demote them.
"""
from django.db import migrations


def create_default_organization(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    if Organization.objects.exists():
        organization = Organization.objects.first()
    else:
        legal_name, tin, phone, address = "My Pharmacy", "", "", ""
        try:
            Settings = apps.get_model("settings_app", "PharmacySettings")
            existing = Settings.objects.first()
            if existing:
                legal_name = getattr(existing, "pharmacy_name", "") or legal_name
                tin = getattr(existing, "tin_number", "") or ""
                phone = getattr(existing, "phone", "") or ""
                address = getattr(existing, "address", "") or ""
        except LookupError:
            pass

        organization = Organization.objects.create(
            legal_name=legal_name, trade_name=legal_name, tin=tin,
            phone=phone, address=address, currency="ETB", status="ACTIVE",
        )
        organization.code = f"ORG-{organization.pk:03d}"
        organization.save(update_fields=["code"])

    # Everything a company owns.
    for app_label, model_name in [
        ("branches", "Branch"),
        ("medicine", "Category"),
        ("medicine", "Medicine"),
        ("suppliers", "Supplier"),
        ("customers", "Customer"),
        ("sales", "Sale"),
        ("purchases", "PurchaseInvoice"),
    ]:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        model.objects.filter(organization__isnull=True).update(
            organization_id=organization.pk
        )

    # Staff, except platform staff, whose null organization is meaningful.
    User = apps.get_model("accounts", "User")
    User.objects.filter(organization__isnull=True).exclude(
        role="SYSTEM_ADMIN"
    ).update(organization_id=organization.pk)


def unassign(apps, schema_editor):
    """Reverse only detaches rows; the organization row itself is left for a
    human to remove, since deleting it would cascade through every table."""
    for app_label, model_name in [
        ("branches", "Branch"), ("medicine", "Category"), ("medicine", "Medicine"),
        ("suppliers", "Supplier"), ("customers", "Customer"),
        ("sales", "Sale"), ("purchases", "PurchaseInvoice"), ("accounts", "User"),
    ]:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        model.objects.update(organization_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("accounts", "0003_user_organization_alter_user_role"),
        ("branches", "0003_branch_organization"),
        ("medicine", "0004_category_organization_medicine_organization"),
        ("suppliers", "0002_supplier_organization"),
        ("customers", "0003_customer_organization"),
        ("sales", "0004_sale_organization"),
        ("purchases", "0004_purchaseinvoice_organization"),
        ("settings_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_organization, unassign),
    ]
