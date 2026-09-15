"""
Tests for branch isolation, transfers, the stock ledger and stocktakes.

Branch isolation is a data-leak risk, not merely a UI concern, so it is
tested at the service layer where the guarantee actually lives.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Role, User
from apps.branches.models import Branch, BranchStock
from apps.inventory.allocation import batch_quantity, verify_consistency
from apps.inventory.batches import StockBatch
from apps.inventory.models import MovementType, StockLedger, StockTake
from apps.inventory.services import apply_stock_movement
from apps.inventory.stocktake import StockTakeStatus
from apps.inventory.stocktake_services import (
    cancel_stocktake, open_stocktake, post_stocktake, reorder_suggestions,
)
from apps.inventory.transfers import transfer_stock
from apps.medicine.models import Category, Medicine
from apps.sales.models import PaymentMethod
from apps.sales.services import complete_sale


class MultiBranchTestCase(TestCase):
    def setUp(self):
        self.main = Branch.objects.create(name="Main", is_main=True)
        self.bole = Branch.objects.create(name="Bole")
        self.user = User.objects.create_user(
            username="tester", password="TestPass#2026", role=Role.ADMINISTRATOR
        )
        self.category = Category.objects.create(name="General")
        self.product = Medicine.objects.create(
            name="Widget", category=self.category,
            purchase_price=Decimal("20.00"), selling_price=Decimal("50.00"),
            tax_percent=Decimal("0.00"), discount_percent=Decimal("0.00"),
            quantity=0, reorder_level=5,
            expiry_date=date.today() + timedelta(days=365),
        )

    def stock_branch(self, branch, quantity, unit_cost="20.00", expiry_days=365):
        StockBatch.objects.create(
            branch=branch, medicine=self.product, unit_cost=Decimal(unit_cost),
            quantity_received=quantity, quantity_remaining=quantity,
            expiry_date=date.today() + timedelta(days=expiry_days),
            source="PURCHASE",
        )
        row = BranchStock.get_or_create_for(branch, self.product)
        row.quantity = quantity
        row.save(update_fields=["quantity", "updated_at"])


class BranchIsolationTests(MultiBranchTestCase):
    def test_a_branch_cannot_sell_another_branch_stock(self):
        self.stock_branch(self.main, 100)
        # Bole has none at all.
        with self.assertRaises(ValidationError):
            complete_sale(
                cart=[{"medicine_id": self.product.pk, "quantity": 1,
                       "discount_percent": Decimal("0")}],
                customer=None, payment_method=PaymentMethod.CASH,
                amount_paid=Decimal("500"), user=self.user, branch=self.bole,
            )
        self.assertEqual(self.product.stock_at(self.main), 100)

    def test_selling_at_one_branch_leaves_the_other_untouched(self):
        self.stock_branch(self.main, 100)
        self.stock_branch(self.bole, 50)

        complete_sale(
            cart=[{"medicine_id": self.product.pk, "quantity": 10,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.bole,
        )
        self.assertEqual(self.product.stock_at(self.bole), 40)
        self.assertEqual(self.product.stock_at(self.main), 100)

    def test_medicine_quantity_is_the_sum_across_branches(self):
        self.stock_branch(self.main, 100)
        self.stock_branch(self.bole, 50)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 150)

    def test_branches_keep_independent_reorder_levels(self):
        self.stock_branch(self.main, 100)
        self.stock_branch(self.bole, 50)
        main_row = BranchStock.objects.get(branch=self.main, medicine=self.product)
        bole_row = BranchStock.objects.get(branch=self.bole, medicine=self.product)
        # Main holds 100 with a high threshold, so it counts as low; Bole
        # holds 50 against a threshold of 5, so it does not. Same product,
        # opposite verdicts — which is the point of per-branch levels.
        main_row.reorder_level = 120
        main_row.save()
        bole_row.refresh_from_db()
        self.assertEqual(bole_row.reorder_level, 5)
        self.assertTrue(main_row.is_low_stock)
        self.assertFalse(bole_row.is_low_stock)

    def test_only_one_branch_is_main(self):
        third = Branch.objects.create(name="Gondar", is_main=True)
        self.assertEqual(Branch.objects.filter(is_main=True).count(), 1)
        self.assertEqual(Branch.objects.get(is_main=True), third)


class TransferTests(MultiBranchTestCase):
    def test_transfer_moves_stock_and_carries_cost(self):
        self.stock_branch(self.main, 100, unit_cost="1.50")
        created = transfer_stock(
            medicine=self.product, quantity=40, source_branch=self.main,
            destination_branch=self.bole, user=self.user,
        )
        self.assertEqual(self.product.stock_at(self.main), 60)
        self.assertEqual(self.product.stock_at(self.bole), 40)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].unit_cost, Decimal("1.50"))
        self.assertEqual(created[0].source, "TRANSFER")

    def test_transfer_carries_expiry_so_fefo_still_works(self):
        self.stock_branch(self.main, 10, unit_cost="5.00", expiry_days=45)
        created = transfer_stock(
            medicine=self.product, quantity=5, source_branch=self.main,
            destination_branch=self.bole,
        )
        self.assertEqual(created[0].expiry_date,
                         date.today() + timedelta(days=45))

    def test_transfer_does_not_create_or_destroy_stock(self):
        self.stock_branch(self.main, 100)
        self.product.refresh_from_db()
        before = self.product.quantity
        transfer_stock(medicine=self.product, quantity=40,
                       source_branch=self.main, destination_branch=self.bole)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, before)

    def test_cannot_transfer_more_than_held(self):
        self.stock_branch(self.main, 10)
        with self.assertRaises(ValidationError):
            transfer_stock(medicine=self.product, quantity=11,
                           source_branch=self.main, destination_branch=self.bole)
        self.assertEqual(self.product.stock_at(self.main), 10)

    def test_cannot_transfer_to_the_same_branch(self):
        self.stock_branch(self.main, 10)
        with self.assertRaises(ValidationError):
            transfer_stock(medicine=self.product, quantity=1,
                           source_branch=self.main, destination_branch=self.main)

    def test_cannot_transfer_to_an_inactive_branch(self):
        self.stock_branch(self.main, 10)
        self.bole.is_active = False
        self.bole.save()
        with self.assertRaises(ValidationError):
            transfer_stock(medicine=self.product, quantity=1,
                           source_branch=self.main, destination_branch=self.bole)


class StockLedgerTests(MultiBranchTestCase):
    def test_ledger_sums_to_current_stock(self):
        """The property that makes the ledger an audit trail rather than a log."""
        self.stock_branch(self.main, 100)
        StockLedger.objects.all().delete()   # ignore fixture noise
        BranchStock.objects.filter(branch=self.main, medicine=self.product).update(
            quantity=100
        )

        complete_sale(
            cart=[{"medicine_id": self.product.pk, "quantity": 30,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.main,
        )
        apply_stock_movement(
            medicine_id=self.product.pk, movement_type=MovementType.STOCK_OUT,
            quantity=5, branch=self.main, reason="breakage", user=self.user,
        )
        transfer_stock(medicine=self.product, quantity=20,
                       source_branch=self.main, destination_branch=self.bole)

        entries = StockLedger.objects.filter(branch=self.main, medicine=self.product)
        net_change = sum(e.quantity_change for e in entries)
        self.assertEqual(100 + net_change, self.product.stock_at(self.main))

    def test_every_cause_is_recorded(self):
        self.stock_branch(self.main, 100)
        StockLedger.objects.all().delete()

        sale = complete_sale(
            cart=[{"medicine_id": self.product.pk, "quantity": 10,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.main,
        )
        transfer_stock(medicine=self.product, quantity=10,
                       source_branch=self.main, destination_branch=self.bole)
        from apps.sales.services import void_sale
        void_sale(sale=sale, user=self.user, reason="test")

        sources = set(StockLedger.objects.values_list("source", flat=True))
        for expected in ("SALE", "TRANSFER_OUT", "TRANSFER_IN", "SALE_VOID"):
            self.assertIn(expected, sources)

    def test_ledger_records_running_balance(self):
        self.stock_branch(self.main, 50)
        StockLedger.objects.all().delete()
        apply_stock_movement(
            medicine_id=self.product.pk, movement_type=MovementType.STOCK_OUT,
            quantity=5, branch=self.main, reason="damage", user=self.user,
        )
        entry = StockLedger.objects.filter(branch=self.main).latest("pk")
        self.assertEqual(entry.balance_before - entry.balance_after, 5)
        self.assertEqual(entry.balance_after, self.product.stock_at(self.main))


class StocktakeTests(MultiBranchTestCase):
    def setUp(self):
        super().setUp()
        self.stock_branch(self.main, 100)

    def test_opening_freezes_expected_quantities(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        line = stocktake.lines.get(medicine=self.product)
        self.assertEqual(line.expected_quantity, 100)

        # A sale during the count must not change the frozen figure.
        complete_sale(
            cart=[{"medicine_id": self.product.pk, "quantity": 10,
                   "discount_percent": Decimal("0")}],
            customer=None, payment_method=PaymentMethod.CASH,
            amount_paid=Decimal("5000"), user=self.user, branch=self.main,
        )
        line.refresh_from_db()
        self.assertEqual(line.expected_quantity, 100)

    def test_only_one_open_stocktake_per_branch(self):
        open_stocktake(branch=self.main, user=self.user)
        with self.assertRaises(ValidationError):
            open_stocktake(branch=self.main, user=self.user)

    def test_uncounted_lines_are_left_untouched_on_posting(self):
        """The most dangerous default this feature could have had."""
        other = Medicine.objects.create(
            name="Other", category=self.category,
            purchase_price=Decimal("1.00"), selling_price=Decimal("2.00"),
            tax_percent=Decimal("0.00"), discount_percent=Decimal("0.00"),
            quantity=0, reorder_level=5,
            expiry_date=date.today() + timedelta(days=365),
        )
        row = BranchStock.get_or_create_for(self.main, other)
        row.quantity = 77
        row.save()

        stocktake = open_stocktake(branch=self.main, user=self.user)
        counted = stocktake.lines.get(medicine=self.product)
        counted.counted_quantity = 94      # 6 missing
        counted.save()
        # The other line is deliberately left uncounted.

        result = post_stocktake(stocktake=stocktake, user=self.user)

        self.assertEqual(other.stock_at(self.main), 77)   # untouched
        self.assertEqual(self.product.stock_at(self.main), 94)
        self.assertEqual(result["adjustments"], 1)
        self.assertGreaterEqual(result["lines_uncounted"], 1)

    def test_posting_records_the_variance_and_closes_the_count(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        line = stocktake.lines.get(medicine=self.product)
        line.counted_quantity = 90
        line.save()
        self.assertEqual(line.variance, -10)

        post_stocktake(stocktake=stocktake, user=self.user)
        stocktake.refresh_from_db()
        self.assertEqual(stocktake.status, StockTakeStatus.POSTED)
        self.assertEqual(self.product.stock_at(self.main), 90)

    def test_cannot_post_twice(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        line = stocktake.lines.get(medicine=self.product)
        line.counted_quantity = 95
        line.save()
        post_stocktake(stocktake=stocktake, user=self.user)
        with self.assertRaises(ValidationError):
            post_stocktake(stocktake=stocktake, user=self.user)

    def test_cannot_post_with_nothing_counted(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        with self.assertRaises(ValidationError):
            post_stocktake(stocktake=stocktake, user=self.user)

    def test_posting_keeps_stock_and_batches_consistent(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        line = stocktake.lines.get(medicine=self.product)
        line.counted_quantity = 120       # 20 found
        line.save()
        post_stocktake(stocktake=stocktake, user=self.user)

        _recorded, _batches, consistent = verify_consistency(
            self.product, branch=self.main
        )
        self.assertTrue(consistent)
        self.assertEqual(batch_quantity(self.product, branch=self.main), 120)

    def test_cancelling_changes_no_stock(self):
        stocktake = open_stocktake(branch=self.main, user=self.user)
        line = stocktake.lines.get(medicine=self.product)
        line.counted_quantity = 1
        line.save()
        cancel_stocktake(stocktake=stocktake, user=self.user)
        stocktake.refresh_from_db()
        self.assertEqual(stocktake.status, StockTakeStatus.CANCELLED)
        self.assertEqual(self.product.stock_at(self.main), 100)


class ReorderPlanTests(MultiBranchTestCase):
    def test_products_above_reorder_level_are_not_suggested(self):
        self.stock_branch(self.main, 100)
        suggestions = reorder_suggestions(branch=self.main)
        names = [s["medicine"].name for s in suggestions]
        self.assertNotIn("Widget", names)

    def test_out_of_stock_products_are_suggested_first(self):
        self.stock_branch(self.main, 0)
        suggestions = reorder_suggestions(branch=self.main)
        self.assertTrue(suggestions)
        self.assertTrue(suggestions[0]["is_out"])
        self.assertGreater(suggestions[0]["suggested_quantity"], 0)

    def test_no_sales_history_gives_no_days_of_cover(self):
        self.stock_branch(self.main, 1)
        suggestion = next(s for s in reorder_suggestions(branch=self.main)
                          if s["medicine"] == self.product)
        self.assertIsNone(suggestion["days_of_cover"])
