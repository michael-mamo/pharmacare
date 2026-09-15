"""Tests for the standard catalogue and registration."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.branches.models import Branch
from apps.catalogue.models import (
    CatalogueCategory, CatalogueProduct, DataSource, DosageForm, ScheduleClass,
)
from apps.catalogue.services import (
    catalogue_coverage, register_product, unregistered_products,
)
from apps.medicine.models import Category, Medicine


class CatalogueProductTests(TestCase):
    def setUp(self):
        self.category = CatalogueCategory.objects.create(name="Analgesics")

    def make(self, **kwargs):
        defaults = dict(
            generic_name="Paracetamol", strength="500mg",
            dosage_form=DosageForm.TABLET, category=self.category,
            schedule=ScheduleClass.OTC, data_source=DataSource.STARTER,
        )
        defaults.update(kwargs)
        return CatalogueProduct.objects.create(**defaults)

    def test_display_name_is_canonical(self):
        product = self.make()
        self.assertEqual(product.display_name, "Paracetamol 500mg Tablet")

    def test_brand_appears_in_parentheses(self):
        product = self.make(brand_name="Panadol")
        self.assertEqual(product.display_name, "Paracetamol 500mg Tablet (Panadol)")

    def test_prescription_flag_follows_the_legal_class(self):
        self.assertFalse(self.make().requires_prescription)
        self.assertTrue(self.make(strength="1g", schedule=ScheduleClass.POM)
                        .requires_prescription)
        self.assertTrue(self.make(strength="250mg", schedule=ScheduleClass.CONTROLLED)
                        .requires_prescription)

    def test_only_authority_sources_count_as_verified(self):
        self.assertFalse(self.make().is_verified_source)                      # STARTER
        self.assertFalse(self.make(strength="100mg",
                                   data_source=DataSource.LOCAL).is_verified_source)
        self.assertTrue(self.make(strength="200mg",
                                  data_source=DataSource.EFDA).is_verified_source)
        self.assertTrue(self.make(strength="300mg",
                                  data_source=DataSource.WHO_EML).is_verified_source)

    def test_same_identity_cannot_be_created_twice(self):
        self.make()
        with self.assertRaises(Exception):
            self.make()

    def test_different_strengths_are_different_products(self):
        self.make(strength="500mg")
        self.make(strength="1g")
        self.assertEqual(CatalogueProduct.objects.count(), 2)


class RegistrationTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name="Main", is_main=True)
        self.own_category = Category.objects.create(name="Shelf A")
        self.catalogue_category = CatalogueCategory.objects.create(name="Analgesics")
        self.product = CatalogueProduct.objects.create(
            generic_name="Amoxicillin", strength="500mg",
            dosage_form=DosageForm.CAPSULE, category=self.catalogue_category,
            schedule=ScheduleClass.POM, default_unit="CAPSULE",
            data_source=DataSource.STARTER,
        )

    def register(self, **kwargs):
        defaults = dict(
            catalogue_product=self.product, category=self.own_category,
            purchase_price=Decimal("4.50"), selling_price=Decimal("7.00"),
            quantity=100, reorder_level=20,
            expiry_date=date.today() + timedelta(days=400),
        )
        defaults.update(kwargs)
        return register_product(**defaults)

    def test_registration_copies_the_standard_identity(self):
        medicine = self.register()
        self.assertEqual(medicine.catalogue_product, self.product)
        self.assertEqual(medicine.generic_name, "Amoxicillin")
        self.assertEqual(medicine.unit, "CAPSULE")

    def test_prescription_flag_comes_from_the_catalogue_not_the_caller(self):
        """A prescription-only medicine must not be registerable as over-counter."""
        medicine = self.register()
        self.assertTrue(medicine.requires_prescription)

    def test_cannot_register_the_same_product_twice(self):
        first = self.register()
        with self.assertRaises(ValidationError) as caught:
            self.register()
        self.assertIn(first.code, str(caught.exception))
        self.assertEqual(Medicine.objects.filter(catalogue_product=self.product).count(), 1)

    def test_medicine_requires_an_expiry_date(self):
        with self.assertRaises(ValidationError):
            self.register(expiry_date=None)

    def test_a_device_may_be_registered_without_expiry(self):
        device = CatalogueProduct.objects.create(
            generic_name="Digital Thermometer", dosage_form=DosageForm.DEVICE,
            product_type="DEVICE", default_unit="PIECE",
            schedule=ScheduleClass.OTC, data_source=DataSource.STARTER,
        )
        medicine = register_product(
            catalogue_product=device, category=self.own_category,
            purchase_price=Decimal("200"), selling_price=Decimal("320"),
            quantity=5, expiry_date=None,
        )
        self.assertIsNone(medicine.expiry_date)

    def test_blank_barcodes_do_not_collide(self):
        """Medicine.barcode is unique with null=True, so blanks must be NULL."""
        self.register()
        second = CatalogueProduct.objects.create(
            generic_name="Cetirizine", strength="10mg",
            dosage_form=DosageForm.TABLET, schedule=ScheduleClass.OTC,
            data_source=DataSource.STARTER,
        )
        medicine = register_product(
            catalogue_product=second, category=self.own_category,
            purchase_price=Decimal("1"), selling_price=Decimal("2"),
            expiry_date=date.today() + timedelta(days=200),
        )
        self.assertIsNone(medicine.barcode)

    def test_opening_quantity_reaches_the_branch(self):
        medicine = self.register(quantity=100)
        self.assertEqual(medicine.stock_at(self.branch), 100)

    def test_coverage_counts_linked_and_unlinked_products(self):
        self.register()
        Medicine.objects.create(
            name="Hand-typed product", category=self.own_category,
            purchase_price=Decimal("1"), selling_price=Decimal("2"),
            tax_percent=Decimal("0"), discount_percent=Decimal("0"),
            quantity=0, reorder_level=1,
            expiry_date=date.today() + timedelta(days=100),
        )
        coverage = catalogue_coverage()
        self.assertEqual(coverage["registered"], 1)
        self.assertEqual(coverage["unlinked"], 1)
        self.assertEqual(coverage["linked_percent"], 50)

    def test_registered_products_drop_out_of_the_unregistered_list(self):
        self.assertIn(self.product, unregistered_products())
        self.register()
        self.assertNotIn(self.product, unregistered_products())
