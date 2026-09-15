"""
Moves an existing single-branch installation onto the multi-branch model.

Anyone upgrading already has stock, sales, purchases and users that predate
branches. Rather than leaving those rows unattributed — which would make
every branch report incomplete and every stock check wrong — this migration:

  1. creates a "Main Branch" (unless branches already exist),
  2. copies each product's `quantity` and `reorder_level` into a BranchStock
     row for it,
  3. stamps existing batches, sales, purchases and stock movements with it,
  4. assigns existing staff to it, leaving Administrators unassigned so they
     retain access across all branches.

It is written to be safe to run on an empty database too, so a fresh install
gets a usable Main Branch out of the box.

The reverse operation intentionally only removes the branch rows; it does not
try to unpick the FK stamps, because the forward direction is not lossy and
re-running it is harmless.
"""
from django.db import migrations


def create_main_branch(apps, schema_editor):
    Branch = apps.get_model("branches", "Branch")
    BranchStock = apps.get_model("branches", "BranchStock")
    Medicine = apps.get_model("medicine", "Medicine")
    User = apps.get_model("accounts", "User")
    StockBatch = apps.get_model("inventory", "StockBatch")
    StockMovement = apps.get_model("inventory", "StockMovement")
    Sale = apps.get_model("sales", "Sale")
    PurchaseInvoice = apps.get_model("purchases", "PurchaseInvoice")

    if Branch.objects.exists():
        branch = Branch.objects.filter(is_main=True).first() or Branch.objects.first()
    else:
        branch = Branch.objects.create(
            name="Main Branch",
            code="BR-001",
            is_main=True,
            is_active=True,
            city="",
            address="",
        )
        # code is normally set in Branch.save(), which migrations bypass.
        if not branch.code:
            branch.code = f"BR-{branch.pk:03d}"
            branch.save(update_fields=["code"])

    # 2) Per-branch stock rows from the existing single quantity column.
    rows = []
    for medicine in Medicine.objects.all().only("id", "quantity", "reorder_level"):
        rows.append(BranchStock(
            branch_id=branch.pk,
            medicine_id=medicine.pk,
            quantity=medicine.quantity or 0,
            reorder_level=medicine.reorder_level or 10,
        ))
    if rows:
        BranchStock.objects.bulk_create(rows, ignore_conflicts=True)

    # 3) Stamp existing history so branch-scoped reports are complete.
    StockBatch.objects.filter(branch__isnull=True).update(branch_id=branch.pk)
    StockMovement.objects.filter(branch__isnull=True).update(branch_id=branch.pk)
    Sale.objects.filter(branch__isnull=True).update(branch_id=branch.pk)
    PurchaseInvoice.objects.filter(branch__isnull=True).update(branch_id=branch.pk)

    # 4) Staff. Administrators stay unassigned on purpose: a null branch is
    #    what grants them the cross-branch view.
    User.objects.filter(branch__isnull=True).exclude(role="ADMIN").update(
        branch_id=branch.pk
    )


def remove_main_branch(apps, schema_editor):
    Branch = apps.get_model("branches", "Branch")
    BranchStock = apps.get_model("branches", "BranchStock")
    BranchStock.objects.all().delete()
    Branch.objects.filter(code="BR-001", name="Main Branch").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("branches", "0001_initial"),
        ("accounts", "0002_user_branch"),
        ("inventory", "0003_stockbatch_branch_stockmovement_branch_and_more"),
        ("sales", "0003_sale_branch_sale_sales_sale_branch__97dba9_idx"),
        ("purchases", "0003_purchaseinvoice_branch"),
        ("medicine", "0002_alter_medicine_options_medicine_product_type_and_more"),
    ]

    operations = [
        migrations.RunPython(create_main_branch, remove_main_branch),
    ]
