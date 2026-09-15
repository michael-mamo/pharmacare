"""
Custom User model implementing role-based access control (RBAC) for the
PharmaCare Management System.

Design notes
------------
We extend AbstractUser (rather than AbstractBaseUser) to keep Django's
battle-tested username/password/permission machinery, and add a `role`
field plus a handful of pharmacy-specific attributes. Role checks are
exposed as convenience properties (`is_administrator`, `is_pharmacist`,
...) so views/templates never compare raw strings.
"""
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Fixed set of roles for the pharmacy. Extending this list later is a
    one-line change plus a migration — no other code depends on the literal
    values because all checks go through the properties below."""

    SYSTEM_ADMIN = "SYSTEM_ADMIN", "System Administrator"
    ADMINISTRATOR = "ADMIN", "Administrator"
    PHARMACIST = "PHARMACIST", "Pharmacist"
    CASHIER = "CASHIER", "Cashier"
    STORE_MANAGER = "STORE_MANAGER", "Store Manager"


phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter a valid phone number (7-15 digits, optionally starting with +).",
)


class User(AbstractUser):
    """PharmaCare staff account.

    Customers are intentionally NOT stored here — see apps.customers.Customer
    (Phase 2). This model is exclusively for staff who log in to the system.
    """

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, null=True, blank=True,
        related_name="staff", verbose_name=_("Organization"),
        help_text=_("The pharmacy company this person works for. Blank means "
                    "platform staff, who belong to no company."),
    )
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="staff", verbose_name=_("Branch"),
        help_text=_("The branch this person works at. Administrators may leave this "
                    "blank to work across every branch."),
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CASHIER,
        db_index=True,
        verbose_name="Role",
        help_text="Determines which modules and actions this user can access.",
    )
    phone_number = models.CharField(
        max_length=20, blank=True, validators=[phone_validator], verbose_name="Phone Number"
    )
    profile_image = models.ImageField(
        upload_to="staff_profiles/%Y/%m/", blank=True, null=True, verbose_name="Profile Photo"
    )
    is_active_employee = models.BooleanField(
        default=True,
        verbose_name="Active Employee",
        help_text="Deactivate instead of deleting to preserve audit history.",
    )
    date_joined_pharmacy = models.DateField(
        auto_now_add=True, verbose_name="Date Joined"
    )
    force_password_change = models.BooleanField(
        default=True,
        verbose_name="Must Change Password",
        help_text="When set, the user is redirected to set a new password before "
        "reaching any other page. Enabled by default for new/admin-reset accounts.",
    )
    last_login_ip = models.GenericIPAddressField(
        blank=True, null=True, verbose_name="Last Login IP"
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=[("en", "English"), ("am", "አማርኛ")],
        default="en",
        verbose_name="Preferred Language",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff User"
        verbose_name_plural = "Staff Users"
        ordering = ["-date_joined_pharmacy", "username"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active_employee"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def get_absolute_url(self):
        return reverse("accounts:user_detail", kwargs={"pk": self.pk})

    # ---- Role convenience properties -------------------------------------
    @property
    def is_administrator(self):
        return self.role == Role.ADMINISTRATOR or self.is_superuser

    @property
    def is_pharmacist(self):
        return self.role == Role.PHARMACIST

    @property
    def is_cashier(self):
        return self.role == Role.CASHIER

    @property
    def is_store_manager(self):
        return self.role == Role.STORE_MANAGER

    # ---- Permission helpers used throughout every later phase -------------
    def can_manage_inventory(self):
        """Administrator and Store Manager can adjust/transfer stock."""
        return self.is_administrator or self.is_store_manager

    def can_process_sales(self):
        """Cashier and Pharmacist operate the POS terminal."""
        return self.is_administrator or self.is_cashier or self.is_pharmacist

    def can_view_reports(self):
        """Every role can reach the Reports section, but *which* reports they
        see is filtered per report — see apps.reports.registry, where each
        report declares its own allowed roles. A Cashier, for example, gets
        the sales and customer reports but not purchase or profit."""
        return True

    def can_view_financial_reports(self):
        """Profit and purchase reports expose cost prices and margins —
        same audience as can_view_cost_price."""
        return self.is_administrator or self.is_store_manager

    def can_export_reports(self):
        """Exporting produces a file that leaves the system (email, USB,
        shared drive), so it's held to a tighter standard than viewing on
        screen: Administrator and Store Manager only."""
        return self.is_administrator or self.is_store_manager

    def can_manage_users(self):
        return self.is_administrator

    # ---- Branch access --------------------------------------------------
    def save(self, *args, **kwargs):
        """Assigns the owning organization when the caller did not.

        Platform staff are exempt: their null organization is what grants
        platform scope, so inferring one would silently demote them to an
        ordinary pharmacy user.
        """
        is_new = self._state.adding
        if self.organization_id is None and self.role != Role.SYSTEM_ADMIN:
            from apps.organizations.models import OrganizationOwnedModel

            self.organization = OrganizationOwnedModel._infer_organization()
        if is_new and self.organization_id is None and self.role != Role.SYSTEM_ADMIN:
            # _infer_organization() can legitimately return None — no
            # request context and more than one organization already
            # exists, so guessing which one owns this account would be
            # worse than refusing outright (see its own docstring). That
            # silent None is exactly what let a pharmacy Administrator
            # account slip through with no organization, which then made
            # it wrongly visible next to System Administrator accounts in
            # a staff list scoped by "organization matches" — the actual
            # incident this check exists to prevent from recurring.
            #
            # Scoped to *creation* only (is_new), not every save: Django's
            # own login machinery calls user.save(update_fields=
            # ["last_login"]) on every successful login, and an already-
            # existing orphaned account (bad legacy data, exactly what
            # this is meant to catch) must still be able to log in and be
            # fixed — raising here unconditionally would instead lock
            # that account out entirely the moment this shipped, which is
            # a worse outcome than the bug it's closing. Find existing
            # orphans with `manage.py audit_orphaned_users` instead.
            raise ValueError(
                f"Refusing to create user '{self.username}' (role={self.role}) "
                "with no organization. Every non-platform-staff account must "
                "belong to exactly one pharmacy. If you're creating this outside "
                "a normal web request, set .organization explicitly before "
                "saving, or wrap the call in `with set_current_organization(org):` "
                "(apps.organizations.models)."
            )
        super().save(*args, **kwargs)

    # ---- Platform vs company ------------------------------------------
    def is_platform_staff(self):
        """Platform staff run the service itself, across all companies.

        Deliberately *not* the same as being a pharmacy Administrator: a
        pharmacy admin has full power inside their own company and none
        outside it.
        """
        return self.role == Role.SYSTEM_ADMIN

    def can_manage_organizations(self):
        return self.is_platform_staff()

    @property
    def is_system_admin(self):
        return self.role == Role.SYSTEM_ADMIN

    def can_access_all_branches(self):
        """Administrators and platform staff see across branches. Everyone else is scoped to
        the branch they work at — a Gondar cashier has no business reading
        Bole's takings."""
        return self.is_administrator

    def can_manage_branches(self):
        """Creating, editing or deactivating a branch is an Administrator task."""
        return self.is_administrator or self.is_platform_staff()

    def accessible_branches(self):
        """Branches this user may look at, as a queryset."""
        from apps.branches.models import Branch

        if self.can_access_all_branches():
            return Branch.objects.filter(is_active=True)
        if self.branch_id:
            return Branch.objects.filter(pk=self.branch_id)
        return Branch.objects.none()

    def default_branch(self):
        """Where this user starts. Administrators land on the main branch; a
        branch-assigned user always gets their own."""
        from apps.branches.models import Branch

        if self.branch_id:
            return self.branch
        return Branch.objects.filter(is_main=True, is_active=True).first() or \
            Branch.objects.filter(is_active=True).first()

    def may_use_branch(self, branch):
        if branch is None:
            return False
        if self.can_access_all_branches():
            return branch.is_active
        return self.branch_id == branch.pk

    def can_manage_settings(self):
        return self.is_administrator

    # ---- Phase 2: Catalog & CRM permissions --------------------------------
    # These intentionally differ by role and by action (view vs. write vs.
    # delete), not just by page — see README's "Phase 2 access matrix" for
    # the full table this implements.
    def can_manage_catalog(self):
        """Create/edit/delete Medicines and Categories: Administrator and
        Store Manager only. Pharmacist and Cashier get read-only access."""
        return self.is_administrator or self.is_store_manager

    def can_view_suppliers(self):
        """Suppliers are purchasing/business data — Cashiers have no need
        to see them at all, unlike Medicines/Categories which they still
        need to browse for a sale."""
        return self.is_administrator or self.is_store_manager or self.is_pharmacist

    def can_manage_suppliers(self):
        return self.is_administrator or self.is_store_manager

    def can_view_cost_price(self):
        """Purchase/cost price is commercially sensitive: visible to
        Administrator and Store Manager only. Pharmacist and Cashier see
        selling price alone, everywhere a price is shown."""
        return self.is_administrator or self.is_store_manager

    def can_edit_customers(self):
        """All operational roles can register/update a customer at the
        counter — this is a day-to-day task, not a management one."""
        return True

    def can_delete_customers(self):
        return self.is_administrator or self.is_store_manager

    # ---- Phase 3: Purchases & Inventory permissions ------------------------
    def can_view_purchases(self):
        """Purchase invoices carry cost prices — the same commercially
        sensitive data as Medicine.purchase_price — so they're restricted
        to the same roles that can already see cost price."""
        return self.is_administrator or self.is_store_manager

    def can_manage_purchases(self):
        return self.is_administrator or self.is_store_manager

    def can_delete_purchases(self):
        """Deleting a purchase reverses its stock effect — a step with
        real financial-record implications, so it's tightened one notch
        further than creating one: Administrator only."""
        return self.is_administrator

    def can_view_inventory_reports(self):
        """Stock levels (current/low/out-of-stock) are operational
        information a Pharmacist needs to know what to dispense or flag
        for reorder — unlike Purchases, this isn't financially sensitive,
        so Pharmacist gets read access here where they don't for Purchases."""
        return self.is_administrator or self.is_store_manager or self.is_pharmacist

    def can_manage_stock_movements(self):
        """Recording Stock In/Out/Adjustment/Transfer changes the system's
        source of truth for quantity — Administrator and Store Manager
        only, matching can_manage_inventory."""
        return self.is_administrator or self.is_store_manager

    # ---- Phase 4: Sales / POS permissions ----------------------------------
    def can_operate_pos(self):
        """Who actually rings up a sale at the counter: Cashier and
        Pharmacist (plus Administrator). Note the Store Manager is
        deliberately excluded — their role is stock and purchasing, not
        the till — which is the inverse of the Purchases permissions."""
        return self.is_administrator or self.is_cashier or self.is_pharmacist

    def can_view_sales(self):
        """Everyone can see the sales history: Cashiers need to reprint a
        receipt, the Store Manager needs sales figures to plan reordering."""
        return True

    def can_void_sales(self):
        """Voiding returns stock and reverses a financial record —
        Administrator only, matching can_delete_purchases."""
        return self.is_administrator
