"""
Tests for stock costing and sale integrity.

These cover the behaviours that would be most expensive to get wrong: the
cost recorded against a sale, the guarantee that stock cannot go negative,
and that voiding a sale restores exactly what it took.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Role, User
from apps.branches.models import Branch, BranchStock
from apps.inventory.allocation import (
    batch_quantity, ensure_opening_batch, stock_value, verify_consistency,
    weighted_average_cost,
)
from apps.inventory.batches import StockBatch
from apps.inventory.transfers import transfer_stock
from apps.medicine.models import Category, Medicine
from apps.sales.models import PaymentMethod, SaleStatus
from apps.sales.services import complete_sale, void_sale


class StockTestCase(TestCase):
    """Shared fixtures: one branch, one product, a user to act as."""

    def setUp(self):
        self.branch = Branch.objects.create(name="Main", is_main=True)
        self.user = User.objects.create_user(
            username="tester", password="TestPass#2026", role=Role.ADMINISTRATOR
        )
        self.category = Category.objects.create(name="General")

    def make_product(self, name="Test Product", purchase="20.00", selling="50.00",
                     quantity=0, tax="0.00", expiry_days=365):
        return Medicine.objects.create(
            name=name, category=self.category,
            purchase_price=Decimal(purchase), selling_price=Decimal(selling),
            tax_percent=Decimal(tax), discount_percent=Decimal("0.00"),
            quantity=quantity, reorder_level=5,
            expiry_date=date.today() + timedelta(days=expiry_days),
        )

    def add_batch(self, product, quantity, unit_cost, expiry_days=365, branch=None):
        return StockBatch.objects.create(
            branch=branch or self.branch, medicine=product,
            unit_cost=Decimal(str(unit_cost)),
            quantity_received=quantity, quantity_remaining=quantity,
            expiry_date=date.today() + timedelta(days=expiry_days),
            source="PURCHASE",
        )

    def set_stock(self, product, quantity, branch=None):
        row = BranchStock.get_or_create_for(branch or self.branch, product)
        row.quantity = quantity
        row.save(update_fields=["quantity", "updated_at"])
        return row


class FefoCostingTests(StockTestCase):
    def test_sale_draws_from_the_soonest_expiring_batch_first(self):
        product = self.make_product()
        self.add_batch(product, 40, "20.00", expiry_days=100)   # expires first
        self.add_batch(product, 100, "30.00", expiry_days=500)
        self.set_stock(product, 140)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 50,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        item = sale.items.get()
        allocations = list(item.cost_allocations.order_by("pk"))

        self.assertEqual(len(allocations), 2)
        self.assertEqual((allocations[0].quantity, allocations[0].unit_cost),
                         (40, Decimal("20.00")))
        self.assertEqual((allocations[1].quantity, allocations[1].unit_cost),
                         (10, Decimal("30.00")))
        # 40x20 + 10x30 = 1100, over 50 units = 22.00 each
        self.assertEqual(item.line_cost, Decimal("1100.00"))
        self.assertEqual(item.unit_cost, Decimal("22.00"))

    def test_fefo_uses_expiry_not_arrival_order(self):
        """A batch received later but expiring sooner must go first."""
        product = self.make_product()
        self.add_batch(product, 10, "10.00", expiry_days=900)   # received first
        self.add_batch(product, 10, "99.00", expiry_days=30)    # expires first
        self.set_stock(product, 20)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 5,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        self.assertEqual(sale.items.get().unit_cost, Decimal("99.00"))

    def test_later_purchase_does_not_change_an_earlier_sale(self):
        """The guarantee that makes historical profit trustworthy."""
        product = self.make_product()
        self.add_batch(product, 50, "20.00", expiry_days=100)
        self.set_stock(product, 50)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 10,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        profit_before = sale.items.get().line_profit

        self.add_batch(product, 100, "45.00", expiry_days=800)
        self.set_stock(product, 140)
        product.purchase_price = Decimal("45.00")
        product.save(update_fields=["purchase_price"])

        sale.refresh_from_db()
        self.assertEqual(sale.items.get().line_profit, profit_before)

    def test_profit_excludes_vat(self):
        product = self.make_product(purchase="20.00", selling="50.00", tax="15.00")
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 10,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        item = sale.items.get()
        self.assertEqual(item.line_subtotal, Decimal("500.00"))
        self.assertEqual(item.line_vat, Decimal("75.00"))
        self.assertEqual(item.line_total, Decimal("575.00"))
        # Profit is on the net-of-VAT figure: 500 - 200 = 300
        self.assertEqual(item.line_profit, Decimal("300.00"))

    def test_discount_is_applied_before_vat(self):
        product = self.make_product(purchase="10.00", selling="100.00", tax="15.00")
        self.add_batch(product, 10, "10.00")
        self.set_stock(product, 10)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 1,
                   "discount_percent": Decimal("10")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("500"), user=self.user, branch=self.branch,
        )
        item = sale.items.get()
        self.assertEqual(item.line_discount, Decimal("10.00"))
        self.assertEqual(item.line_after_discount, Decimal("90.00"))
        self.assertEqual(item.line_vat, Decimal("13.50"))   # 15% of 90, not of 100
        self.assertEqual(item.line_total, Decimal("103.50"))

    def test_weighted_average_cost_and_stock_value(self):
        product = self.make_product()
        self.add_batch(product, 40, "20.00", expiry_days=100)
        self.add_batch(product, 100, "30.00", expiry_days=500)
        self.set_stock(product, 140)

        self.assertEqual(stock_value(product, branch=self.branch),
                         Decimal("3800.00"))       # 40*20 + 100*30
        self.assertEqual(weighted_average_cost(product, branch=self.branch),
                         Decimal("27.14"))          # 3800 / 140


class OversellTests(StockTestCase):
    def test_cannot_sell_more_than_stock(self):
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        with self.assertRaises(ValidationError):
            complete_sale(
                cart=[{"medicine_id": product.pk, "quantity": 11,
                       "discount_percent": Decimal("0")}],
                customer=None, payment_method=PaymentMethod.CASH,
                amount_paid=Decimal("0"), user=self.user, branch=self.branch,
            )
        self.assertEqual(product.stock_at(self.branch), 10)

    def test_duplicate_cart_lines_are_summed_before_checking(self):
        """Two lines of 6 against 10 stock must fail — they total 12."""
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        with self.assertRaises(ValidationError):
            complete_sale(
                cart=[
                    {"medicine_id": product.pk, "quantity": 6,
                     "discount_percent": Decimal("0")},
                    {"medicine_id": product.pk, "quantity": 6,
                     "discount_percent": Decimal("0")},
                ],
                customer=None, payment_method=PaymentMethod.CASH,
                amount_paid=Decimal("0"), user=self.user, branch=self.branch,
            )
        self.assertEqual(product.stock_at(self.branch), 10)

    def test_duplicate_lines_within_stock_succeed(self):
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        complete_sale(
            cart=[
                {"medicine_id": product.pk, "quantity": 4,
                 "discount_percent": Decimal("0")},
                {"medicine_id": product.pk, "quantity": 3,
                 "discount_percent": Decimal("0")},
            ],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        self.assertEqual(product.stock_at(self.branch), 3)

    def test_zero_and_negative_quantities_are_rejected(self):
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        for bad_quantity in (0, -5):
            with self.subTest(quantity=bad_quantity):
                with self.assertRaises(ValidationError):
                    complete_sale(
                        cart=[{"medicine_id": product.pk, "quantity": bad_quantity,
                               "discount_percent": Decimal("0")}],
                        customer=None, payment_method=PaymentMethod.CASH,
                        amount_paid=Decimal("0"), user=self.user, branch=self.branch,
                    )

    def test_empty_cart_is_rejected(self):
        with self.assertRaises(ValidationError):
            complete_sale(
                cart=[], customer=None, payment_method=PaymentMethod.CASH,
                amount_paid=Decimal("0"), user=self.user, branch=self.branch,
            )

    def test_stock_never_goes_negative_across_a_sequence(self):
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        for _ in range(4):
            complete_sale(
                cart=[{"medicine_id": product.pk, "quantity": 3,
                       "discount_percent": Decimal("0")}],
                customer=None, payment_method=PaymentMethod.CASH,
                amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
            )
            if product.stock_at(self.branch) < 3:
                break
        self.assertGreaterEqual(product.stock_at(self.branch), 0)


class VoidSaleTests(StockTestCase):
    def test_void_restores_stock_to_the_original_batches(self):
        product = self.make_product()
        first = self.add_batch(product, 40, "20.00", expiry_days=100)
        second = self.add_batch(product, 100, "30.00", expiry_days=500)
        self.set_stock(product, 140)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 50,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        void_sale(sale=sale, user=self.user, reason="test")

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.quantity_remaining, 40)
        self.assertEqual(second.quantity_remaining, 100)
        self.assertEqual(product.stock_at(self.branch), 140)

    def test_void_marks_the_sale_and_cannot_be_repeated(self):
        product = self.make_product()
        self.add_batch(product, 10, "20.00")
        self.set_stock(product, 10)

        sale = complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 5,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        void_sale(sale=sale, user=self.user, reason="test")
        sale.refresh_from_db()
        self.assertEqual(sale.status, SaleStatus.VOIDED)

        with self.assertRaises(ValidationError):
            void_sale(sale=sale, user=self.user, reason="again")
        self.assertEqual(product.stock_at(self.branch), 10)


class StockConsistencyTests(StockTestCase):
    def test_branch_stock_always_matches_its_batches(self):
        product = self.make_product()
        self.add_batch(product, 40, "20.00", expiry_days=100)
        self.add_batch(product, 100, "30.00", expiry_days=500)
        self.set_stock(product, 140)

        complete_sale(
            cart=[{"medicine_id": product.pk, "quantity": 50,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.branch,
        )
        recorded, from_batches, consistent = verify_consistency(
            product, branch=self.branch
        )
        self.assertTrue(consistent, f"{recorded} != {from_batches}")
        self.assertEqual(recorded, 90)

    def test_opening_batch_covers_stock_entered_without_a_purchase(self):
        product = self.make_product(quantity=25)
        # Medicine.save seeds BranchStock; batches should follow on demand.
        ensure_opening_batch(product, branch=self.branch)
        self.assertEqual(batch_quantity(product, branch=self.branch), 25)
        _r, _b, consistent = verify_consistency(product, branch=self.branch)
        self.assertTrue(consistent)
