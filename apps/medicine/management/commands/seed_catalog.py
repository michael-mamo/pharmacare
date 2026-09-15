"""
Seeds representative sample data for Phase 2 so the catalog isn't empty on
first run. Safe to re-run — uses get_or_create throughout.

Run `seed_catalogue` first: MEDICINE-type samples here are linked against
the standard catalogue (Medicine.clean() requires this everywhere now), so
if a sample's generic name isn't in the catalogue yet, it's skipped with a
warning rather than created unlinked.

Usage:
    python manage.py seed_catalogue
    python manage.py seed_catalog
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.catalogue.models import CatalogueProduct
from apps.customers.models import Customer
from apps.medicine.models import Category, Medicine, ProductType, Unit
from apps.suppliers.models import Supplier


class Command(BaseCommand):
    help = "Seed sample categories, suppliers, customers, and medicines (run seed_catalogue first)."

    def handle(self, *args, **options):
        today = date.today()

        categories = {}
        for name, desc in [
            ("Analgesics", "Pain relief medication"),
            ("Antibiotics", "Bacterial infection treatment"),
            ("Antihistamines", "Allergy relief medication"),
            ("Vitamins & Supplements", "Nutritional support products"),
            ("Cough & Cold", "Respiratory symptom relief"),
            ("Cosmetics & Skin Care", "Creams, lotions and personal care"),
            ("Dressings & First Aid", "Bandages, gauze, plasters, antiseptics"),
            ("Supports & Devices", "Braces, supports and monitoring devices"),
            ("Baby & Mother Care", "Baby and maternal products"),
        ]:
            cat, created = Category.objects.get_or_create(name=name, defaults={"description": desc})
            categories[name] = cat
            if created:
                self.stdout.write(self.style.SUCCESS(f"Category: {name}"))

        suppliers = {}
        for name, contact, phone, email in [
            ("Addis Pharma Distribution", "Meron Tesfaye", "+251911223344", "sales@addispharma.et"),
            ("EthioMed Suppliers", "Yohannes Girma", "+251922334455", "orders@ethiomed.et"),
            ("Nile Health Imports", "Sara Haile", "+251933445566", "info@nilehealth.et"),
        ]:
            sup, created = Supplier.objects.get_or_create(
                name=name, defaults={"contact_person": contact, "phone": phone, "email": email}
            )
            suppliers[name] = sup
            if created:
                self.stdout.write(self.style.SUCCESS(f"Supplier: {name}"))

        for name, phone, email in [
            ("Kebede Alemu", "+251944556677", "kebede.alemu@example.com"),
            ("Tigist Bekele", "+251955667788", "tigist.bekele@example.com"),
            ("Mulugeta Fikru", "+251966778899", ""),
        ]:
            _, created = Customer.objects.get_or_create(
                name=name, defaults={"phone": phone, "email": email, "loyalty_points": 0}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Customer: {name}"))

        # Non-medicine lines: the counter also sells cosmetics, dressings and
        # devices, and they flow through POS/batches/reports identically.
        sample_medicines = [
            dict(name="Nivea Moisturising Cream 200ml", generic_name="", brand="Nivea",
                 category="Cosmetics & Skin Care", supplier="Nile Health Imports",
                 purchase_price="120.00", selling_price="185.00", quantity=30, reorder_level=8,
                 unit=Unit.JAR, expiry_offset_days=730, product_type=ProductType.COSMETIC),
            dict(name="Elastic Bandage 7.5cm", generic_name="", brand="MediWrap",
                 category="Dressings & First Aid", supplier="EthioMed Suppliers",
                 purchase_price="35.00", selling_price="60.00", quantity=60, reorder_level=15,
                 unit=Unit.ROLL, expiry_offset_days=1095, product_type=ProductType.MEDICAL_SUPPLY),
            dict(name="Sterile Gauze Pads 10x10cm (pack of 10)", generic_name="", brand="MediWrap",
                 category="Dressings & First Aid", supplier="EthioMed Suppliers",
                 purchase_price="45.00", selling_price="75.00", quantity=40, reorder_level=10,
                 unit=Unit.PACK, expiry_offset_days=900, product_type=ProductType.MEDICAL_SUPPLY),
            dict(name="Knee Support Brace (Medium)", generic_name="", brand="OrthoFlex",
                 category="Supports & Devices", supplier="Nile Health Imports",
                 purchase_price="380.00", selling_price="595.00", quantity=12, reorder_level=3,
                 unit=Unit.PIECE, expiry_offset_days=None, product_type=ProductType.MEDICAL_DEVICE),
            dict(name="Digital Blood Pressure Monitor", generic_name="", brand="OmniCare",
                 category="Supports & Devices", supplier="Nile Health Imports",
                 purchase_price="1450.00", selling_price="2190.00", quantity=6, reorder_level=2,
                 unit=Unit.PIECE, expiry_offset_days=None, product_type=ProductType.MEDICAL_DEVICE),
            dict(name="Baby Nappies Size 3 (pack of 40)", generic_name="", brand="SoftCare",
                 category="Baby & Mother Care", supplier="Addis Pharma Distribution",
                 purchase_price="290.00", selling_price="430.00", quantity=25, reorder_level=6,
                 unit=Unit.PACK, expiry_offset_days=1460, product_type=ProductType.BABY_CARE),
            dict(name="Paracetamol 500mg", generic_name="Paracetamol", brand="Fenac",
                 category="Analgesics", supplier="Addis Pharma Distribution",
                 purchase_price="1.50", selling_price="3.00", quantity=500, reorder_level=50,
                 unit=Unit.TABLET, expiry_offset_days=540),
            dict(name="Amoxicillin 250mg", generic_name="Amoxicillin", brand="Amoxil",
                 category="Antibiotics", supplier="EthioMed Suppliers",
                 purchase_price="4.00", selling_price="8.50", quantity=8, reorder_level=30,
                 unit=Unit.CAPSULE, expiry_offset_days=20, requires_prescription=True),
            dict(name="Loratadine 10mg", generic_name="Loratadine", brand="Claritin",
                 category="Antihistamines", supplier="Nile Health Imports",
                 purchase_price="2.00", selling_price="4.50", quantity=200, reorder_level=25,
                 unit=Unit.TABLET, expiry_offset_days=365),
            dict(name="Vitamin C 1000mg", generic_name="Ascorbic Acid", brand="Cevit",
                 category="Vitamins & Supplements", supplier="Addis Pharma Distribution",
                 purchase_price="3.20", selling_price="6.00", quantity=150, reorder_level=20,
                 unit=Unit.TABLET, expiry_offset_days=-10),  # already expired, for testing
            dict(name="Cough Syrup 100ml", generic_name="Dextromethorphan", brand="Benylin",
                 category="Cough & Cold", supplier="EthioMed Suppliers",
                 purchase_price="15.00", selling_price="28.00", quantity=45, reorder_level=15,
                 unit=Unit.BOTTLE, expiry_offset_days=200),
        ]

        for data in sample_medicines:
            if Medicine.objects.filter(name=data["name"]).exists():
                continue
            expiry_offset = data.get("expiry_offset_days")
            product_type = data.get("product_type", ProductType.MEDICINE)

            # As of the standard catalogue rollout, MEDICINE-type stock must
            # be linked to a catalogue record (Medicine.full_clean() enforces
            # this everywhere else); this sample seeder used .objects.create()
            # directly, which skips validation, so it needs its own lookup to
            # stay honest rather than silently creating orphaned medicines.
            # Non-medicine samples (cosmetics, supplies, devices, baby care)
            # are unaffected — they were never meant to need one.
            catalogue_product = None
            if product_type == ProductType.MEDICINE:
                # Prefer a tablet/capsule form when the generic name matches
                # several catalogue entries (e.g. Paracetamol also has a
                # syrup) — these samples are written as solid oral doses.
                catalogue_product = (
                    CatalogueProduct.objects.filter(
                        generic_name__iexact=data["generic_name"], is_active=True,
                        dosage_form__in=["TABLET", "CAPSULE"],
                    ).order_by("strength").first()
                    or CatalogueProduct.objects.filter(
                        generic_name__iexact=data["generic_name"], is_active=True
                    ).first()
                    or CatalogueProduct.objects.filter(
                        generic_name__icontains=data["generic_name"], is_active=True
                    ).order_by("generic_name").first()
                )
                if not catalogue_product:
                    self.stdout.write(self.style.WARNING(
                        f"Skipped {data['name']}: no matching catalogue entry for "
                        f"\"{data['generic_name']}\" — run seed_catalogue first, or "
                        "add it to the catalogue, then re-run this command."
                    ))
                    continue

            Medicine.objects.create(
                product_type=product_type,
                catalogue_product=catalogue_product,
                requires_prescription=data.get("requires_prescription", False),
                name=data["name"],
                generic_name=data["generic_name"],
                brand=data["brand"],
                category=categories[data["category"]],
                supplier=suppliers[data["supplier"]],
                purchase_price=data["purchase_price"],
                selling_price=data["selling_price"],
                quantity=data["quantity"],
                reorder_level=data["reorder_level"],
                unit=data["unit"],
                # Devices and similar durable goods have no expiry date.
                expiry_date=(today + timedelta(days=expiry_offset)) if expiry_offset is not None else None,
                manufacturing_date=today - timedelta(days=365),
                batch_number=f"B{today.year}{data['name'][:2].upper()}",
            )
            self.stdout.write(self.style.SUCCESS(f"Medicine: {data['name']}"))

        self.stdout.write(self.style.SUCCESS("\nSample catalog data ready."))
