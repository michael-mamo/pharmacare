"""
Tests for role permissions and access control.

Access is tested at the HTTP layer rather than by calling the permission
methods, because that is where a real breach would happen: a view that
forgets its mixin passes every unit test on the model and still leaks.
"""
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.branches.models import Branch


class RolePermissionTests(TestCase):
    """The permission predicates themselves."""

    def setUp(self):
        self.branch = Branch.objects.create(name="Main", is_main=True)
        self.users = {}
        for role in (Role.ADMINISTRATOR, Role.PHARMACIST, Role.CASHIER,
                     Role.STORE_MANAGER):
            self.users[role] = User.objects.create_user(
                username=f"user_{role.lower()}", password="TestPass#2026",
                role=role, branch=None if role == Role.ADMINISTRATOR else self.branch,
            )

    def test_cost_price_is_restricted_to_admin_and_store_manager(self):
        self.assertTrue(self.users[Role.ADMINISTRATOR].can_view_cost_price())
        self.assertTrue(self.users[Role.STORE_MANAGER].can_view_cost_price())
        self.assertFalse(self.users[Role.PHARMACIST].can_view_cost_price())
        self.assertFalse(self.users[Role.CASHIER].can_view_cost_price())

    def test_till_excludes_the_store_manager(self):
        """Deliberate inversion of the purchasing permissions."""
        self.assertTrue(self.users[Role.CASHIER].can_operate_pos())
        self.assertTrue(self.users[Role.PHARMACIST].can_operate_pos())
        self.assertTrue(self.users[Role.ADMINISTRATOR].can_operate_pos())
        self.assertFalse(self.users[Role.STORE_MANAGER].can_operate_pos())

    def test_voiding_is_administrator_only(self):
        self.assertTrue(self.users[Role.ADMINISTRATOR].can_void_sales())
        for role in (Role.STORE_MANAGER, Role.PHARMACIST, Role.CASHIER):
            self.assertFalse(self.users[role].can_void_sales())

    def test_exporting_is_tighter_than_viewing(self):
        for role in (Role.ADMINISTRATOR, Role.STORE_MANAGER):
            self.assertTrue(self.users[role].can_view_reports())
            self.assertTrue(self.users[role].can_export_reports())
        for role in (Role.PHARMACIST, Role.CASHIER):
            self.assertTrue(self.users[role].can_view_reports())
            self.assertFalse(self.users[role].can_export_reports())

    def test_only_administrators_span_branches(self):
        self.assertTrue(self.users[Role.ADMINISTRATOR].can_access_all_branches())
        for role in (Role.STORE_MANAGER, Role.PHARMACIST, Role.CASHIER):
            self.assertFalse(self.users[role].can_access_all_branches())

    def test_a_branch_user_may_only_use_their_own_branch(self):
        other = Branch.objects.create(name="Bole")
        cashier = self.users[Role.CASHIER]
        self.assertTrue(cashier.may_use_branch(self.branch))
        self.assertFalse(cashier.may_use_branch(other))
        self.assertTrue(self.users[Role.ADMINISTRATOR].may_use_branch(other))

    def test_administrator_defaults_to_the_main_branch(self):
        self.assertEqual(self.users[Role.ADMINISTRATOR].default_branch(), self.branch)


class PageAccessTests(TestCase):
    """Access control as actually enforced by the views."""

    #: (url name, {role: expected status})
    MATRIX = [
        ("dashboard:home", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 403,
                            Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("sales:pos", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 403,
                       Role.PHARMACIST: 200, Role.CASHIER: 200}),
        ("sales:sale_list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                             Role.PHARMACIST: 200, Role.CASHIER: 200}),
        ("medicine:medicine_create", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                      Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("suppliers:supplier_list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                     Role.PHARMACIST: 200, Role.CASHIER: 403}),
        ("purchases:purchase_create", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                       Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("inventory:overview", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                Role.PHARMACIST: 200, Role.CASHIER: 403}),
        ("inventory:ledger", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                              Role.PHARMACIST: 200, Role.CASHIER: 403}),
        ("inventory:stocktake_list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                      Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("inventory:reorder_plan", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                    Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("catalogue:product_list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                    Role.PHARMACIST: 200, Role.CASHIER: 200}),
        ("catalogue:product_create", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                      Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("branches:branch_list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 403,
                                  Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("audit:list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 403,
                        Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("settings_app:settings", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 403,
                                   Role.PHARMACIST: 403, Role.CASHIER: 403}),
        ("reports:index", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                           Role.PHARMACIST: 200, Role.CASHIER: 200}),
        ("notifications:list", {Role.ADMINISTRATOR: 200, Role.STORE_MANAGER: 200,
                                Role.PHARMACIST: 200, Role.CASHIER: 200}),
    ]

    def setUp(self):
        self.branch = Branch.objects.create(name="Main", is_main=True)
        self.clients = {}
        for role in (Role.ADMINISTRATOR, Role.PHARMACIST, Role.CASHIER,
                     Role.STORE_MANAGER):
            user = User.objects.create_user(
                username=f"u_{role.lower()}", password="TestPass#2026", role=role,
                branch=None if role == Role.ADMINISTRATOR else self.branch,
                force_password_change=False,
            )
            client = Client()
            client.force_login(user)
            self.clients[role] = client

    def _status(self, client, url):
        from django.core.exceptions import PermissionDenied

        try:
            return client.get(url).status_code
        except PermissionDenied:
            return 403

    def test_access_matrix(self):
        for url_name, expectations in self.MATRIX:
            url = reverse(url_name)
            for role, expected in expectations.items():
                with self.subTest(url=url_name, role=role):
                    self.assertEqual(
                        self._status(self.clients[role], url), expected,
                        f"{role} on {url_name}",
                    )

    def test_anonymous_users_are_redirected_to_login(self):
        anonymous = Client()
        for url_name in ("dashboard:home", "sales:pos", "inventory:overview"):
            with self.subTest(url=url_name):
                response = anonymous.get(reverse(url_name))
                self.assertIn(response.status_code, (302, 403))
                if response.status_code == 302:
                    self.assertIn("login", response["Location"])

    def test_cost_columns_are_hidden_from_uncleared_roles(self):
        """A restricted figure must be absent from the HTML, not merely styled away."""
        url = reverse("inventory:aging")
        cleared = self.clients[Role.STORE_MANAGER].get(url).content.decode()
        self.assertIn("Total Stock Value", cleared)

        try:
            restricted = self.clients[Role.PHARMACIST].get(url).content.decode()
        except Exception:
            restricted = ""
        self.assertNotIn("Total Stock Value", restricted)


class PasswordPolicyTests(TestCase):
    def test_new_accounts_must_change_their_password(self):
        branch = Branch.objects.create(name="Main", is_main=True)
        user = User.objects.create_user(
            username="newcomer", password="TempPass#2026",
            role=Role.CASHIER, branch=branch,
        )
        self.assertTrue(user.force_password_change)

    def test_short_passwords_are_rejected(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        with self.assertRaises(DjangoValidationError):
            validate_password("short1!")
