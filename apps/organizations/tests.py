"""
Tenancy tests.

These are the most security-relevant tests in the project. A leak here means
one pharmacy company reading another's sales, stock or staff — so isolation
is asserted at the manager, at the request boundary, and against deliberate
bypass attempts, not merely by checking that a filter exists somewhere.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.medicine.models import Category, Medicine
from apps.organizations.models import (
    Organization, OrganizationStatus, clear_current_organization,
    get_current_organization, set_current_organization, set_strict, unscoped,
)
from apps.suppliers.models import Supplier


class TenancyTestCase(TestCase):
    """Two complete, independent pharmacy companies."""

    def setUp(self):
        clear_current_organization()
        set_strict(False)

        self.alpha = Organization.objects.create(legal_name="Alpha Pharma")
        self.beta = Organization.objects.create(legal_name="Beta Pharma")

        self.alpha_branch = Branch.objects.create(
            name="Alpha Main", is_main=True, organization=self.alpha
        )
        self.beta_branch = Branch.objects.create(
            name="Beta Main", is_main=True, organization=self.beta
        )

        self.alpha_category = Category.objects.create(
            name="Alpha Shelf", organization=self.alpha
        )
        self.beta_category = Category.objects.create(
            name="Beta Shelf", organization=self.beta
        )

        self.alpha_product = self._product("Alpha Widget", self.alpha,
                                           self.alpha_category)
        self.beta_product = self._product("Beta Widget", self.beta,
                                          self.beta_category)

        self.alpha_user = User.objects.create_user(
            username="alpha_admin", password="TestPass#2026",
            role=Role.ADMINISTRATOR, organization=self.alpha,
            force_password_change=False,
        )
        self.beta_user = User.objects.create_user(
            username="beta_admin", password="TestPass#2026",
            role=Role.ADMINISTRATOR, organization=self.beta,
            force_password_change=False,
        )

    def tearDown(self):
        clear_current_organization()
        set_strict(False)

    def keep_only(self, organization):
        """Leaves exactly one organization in the database.

        Note it removes *every* other one, not just the second fixture: the
        initial data migration seeds a default company ("My Pharmacy"), so a
        test database always starts with one already present. Missing that is
        why an earlier version of this helper left two behind and inference
        correctly refused to guess.

        A bare `delete()` is also refused while products exist, because
        Medicine protects its Category — that protection is right, so
        dependants are cleared first rather than weakening the model.
        """
        for other in Organization.objects.exclude(pk=organization.pk):
            Medicine.all_objects.filter(organization=other).delete()
            Category.all_objects.filter(organization=other).delete()
            Branch.all_objects.filter(organization=other).delete()
            User.objects.filter(organization=other).delete()
            other.delete()
        assert Organization.objects.count() == 1

    @staticmethod
    def _product(name, organization, category):
        return Medicine.objects.create(
            name=name, category=category, organization=organization,
            purchase_price=Decimal("10.00"), selling_price=Decimal("20.00"),
            tax_percent=Decimal("0.00"), discount_percent=Decimal("0.00"),
            quantity=0, reorder_level=5,
            expiry_date=date.today() + timedelta(days=365),
        )


class ManagerScopingTests(TenancyTestCase):
    def test_default_manager_filters_to_the_current_organization(self):
        set_current_organization(self.alpha)
        names = set(Medicine.objects.values_list("name", flat=True))
        self.assertEqual(names, {"Alpha Widget"})

        set_current_organization(self.beta)
        names = set(Medicine.objects.values_list("name", flat=True))
        self.assertEqual(names, {"Beta Widget"})

    def test_scoping_applies_to_every_owned_model(self):
        set_current_organization(self.alpha)
        self.assertEqual(Branch.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Medicine.objects.count(), 1)
        self.assertEqual(Branch.objects.get().name, "Alpha Main")

    def test_get_cannot_reach_across_organizations(self):
        set_current_organization(self.alpha)
        with self.assertRaises(Medicine.DoesNotExist):
            Medicine.objects.get(pk=self.beta_product.pk)

    def test_filtering_by_another_organizations_pk_returns_nothing(self):
        """Even knowing the primary key must not help."""
        set_current_organization(self.alpha)
        self.assertFalse(Medicine.objects.filter(pk=self.beta_product.pk).exists())

    def test_unscoped_manager_sees_everything(self):
        set_current_organization(self.alpha)
        self.assertEqual(Medicine.all_objects.count(), 2)

    def test_unscoped_context_manager_suspends_filtering(self):
        set_current_organization(self.alpha)
        self.assertEqual(Medicine.objects.count(), 1)
        with unscoped():
            self.assertEqual(Medicine.objects.count(), 2)
        self.assertEqual(Medicine.objects.count(), 1)

    def test_strict_mode_denies_when_no_organization_is_set(self):
        """A request that fails to resolve an organization must see nothing."""
        clear_current_organization()
        set_strict(True)
        self.assertEqual(Medicine.objects.count(), 0)
        self.assertEqual(Branch.objects.count(), 0)

    def test_commands_without_an_organization_are_unfiltered(self):
        clear_current_organization()
        set_strict(False)
        self.assertEqual(Medicine.objects.count(), 2)


class OwnershipInferenceTests(TenancyTestCase):
    def test_new_records_take_the_current_organization(self):
        set_current_organization(self.beta)
        supplier = Supplier.objects.create(name="Inferred Supplier")
        self.assertEqual(supplier.organization, self.beta)

    def test_owner_is_not_guessed_when_ambiguous(self):
        """Two organizations and no request: the owner is genuinely unknown."""
        clear_current_organization()
        set_strict(False)
        customer = Customer.objects.create(name="Nobody", phone="0911000111")
        self.assertIsNone(customer.organization)

    def test_single_organization_is_inferred_without_a_request(self):
        self.keep_only(self.alpha)
        clear_current_organization()
        supplier = Supplier.objects.create(name="Only Option")
        self.assertEqual(supplier.organization, self.alpha)

    def test_explicit_organization_always_wins(self):
        set_current_organization(self.alpha)
        supplier = Supplier.objects.create(name="Explicit", organization=self.beta)
        self.assertEqual(supplier.organization, self.beta)


class UserOrganizationTests(TenancyTestCase):
    def test_platform_staff_have_no_organization(self):
        system_admin = User.objects.create_user(
            username="platform", password="TestPass#2026", role=Role.SYSTEM_ADMIN,
        )
        self.assertIsNone(system_admin.organization)
        self.assertTrue(system_admin.is_platform_staff())
        self.assertTrue(system_admin.can_manage_organizations())

    def test_a_pharmacy_admin_is_not_platform_staff(self):
        """Full power inside one company is not power over the platform."""
        self.assertFalse(self.alpha_user.is_platform_staff())
        self.assertFalse(self.alpha_user.can_manage_organizations())
        self.assertTrue(self.alpha_user.is_administrator)

    def test_ordinary_users_are_assigned_the_single_organization(self):
        self.keep_only(self.alpha)
        clear_current_organization()
        cashier = User.objects.create_user(
            username="inferred", password="TestPass#2026", role=Role.CASHIER,
        )
        self.assertEqual(cashier.organization, self.alpha)


class RequestIsolationTests(TenancyTestCase):
    """Isolation as enforced through real requests, where a leak would happen."""

    def _client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def test_a_users_organization_comes_from_their_account(self):
        client = self._client_for(self.alpha_user)
        response = client.get(reverse("medicine:medicine_list"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Alpha Widget", body)
        self.assertNotIn("Beta Widget", body)

    def test_each_company_sees_only_its_own_products(self):
        body = self._client_for(self.beta_user).get(
            reverse("medicine:medicine_list")
        ).content.decode()
        self.assertIn("Beta Widget", body)
        self.assertNotIn("Alpha Widget", body)

    def test_another_companys_record_is_not_reachable_by_url(self):
        """The classic insecure-direct-object-reference attempt."""
        client = self._client_for(self.alpha_user)
        response = client.get(
            reverse("medicine:medicine_detail", kwargs={"pk": self.beta_product.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_own_record_is_reachable(self):
        client = self._client_for(self.alpha_user)
        response = client.get(
            reverse("medicine:medicine_detail", kwargs={"pk": self.alpha_product.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_branch_lists_are_isolated(self):
        body = self._client_for(self.alpha_user).get(
            reverse("branches:branch_list")
        ).content.decode()
        self.assertIn("Alpha Main", body)
        self.assertNotIn("Beta Main", body)

    def test_platform_staff_see_nothing_until_they_choose_an_organization(self):
        system_admin = User.objects.create_user(
            username="platform", password="TestPass#2026", role=Role.SYSTEM_ADMIN,
        )
        client = self._client_for(system_admin)
        body = client.get(reverse("medicine:medicine_list")).content.decode()
        self.assertNotIn("Alpha Widget", body)
        self.assertNotIn("Beta Widget", body)

    def test_the_organization_does_not_leak_between_requests(self):
        """State is per-request; a previous tenant must not bleed into the next."""
        self._client_for(self.alpha_user).get(reverse("medicine:medicine_list"))
        self.assertIsNone(get_current_organization())

        body = self._client_for(self.beta_user).get(
            reverse("medicine:medicine_list")
        ).content.decode()
        self.assertNotIn("Alpha Widget", body)


class OrganizationModelTests(TenancyTestCase):
    def test_code_is_generated(self):
        self.assertTrue(self.alpha.code.startswith("ORG-"))
        self.assertNotEqual(self.alpha.code, self.beta.code)

    def test_display_name_prefers_the_trade_name(self):
        self.assertEqual(self.alpha.display_name, "Alpha Pharma")
        self.alpha.trade_name = "Alpha Chemists"
        self.alpha.save()
        self.assertEqual(self.alpha.display_name, "Alpha Chemists")

    def test_suspension_is_recorded(self):
        self.assertTrue(self.alpha.is_active)
        self.alpha.status = OrganizationStatus.SUSPENDED
        self.alpha.save()
        self.assertFalse(self.alpha.is_active)

    def test_an_organization_with_trading_data_cannot_be_deleted(self):
        """Deleting a company must not silently destroy its history."""
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.alpha.delete()

    def test_counts_span_the_whole_organization(self):
        self.assertEqual(self.alpha.branch_count, 1)
        self.assertEqual(self.alpha.user_count, 1)
