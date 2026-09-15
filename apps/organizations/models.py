"""
Multi-tenancy: the Organization (pharmacy company) and how data is scoped to it.

The design problem
------------------
The system already isolates data by *branch*. Tenancy adds a layer above
that: one platform hosting several independent pharmacy companies, where
Company A must never see Company B's anything.

The naive way to do that is to add `.filter(organization=...)` at every query
site. There are already 118 of them and the accounting engine will roughly
double that, so relying on every future call site remembering is not a
control — it is a hope. One forgotten filter is a silent cross-company data
leak, and in the ledger it would be unnoticeable.

So scoping is enforced by the **default manager** instead. A model inheriting
`OrganizationOwnedModel` filters to the current organization automatically,
and views need no change at all. Code that genuinely needs to cross
organizations must say so explicitly via `all_organizations()`, which is
greppable in review — the safe path is the default and the dangerous one is
visible.

Single-company today, SaaS-ready
--------------------------------
Running with exactly one organization behaves identically to before. Nothing
here has to change when more are added; only the seeding does.
"""
from asgiref.local import Local
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

#: Request-scoped current organization. `asgiref.local.Local` rather than
#: threading.local so it behaves correctly under ASGI and async views, where
#: one thread may serve several requests.
_state = Local()

phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-()]{7,20}$",
    message=_("Enter a valid phone number."),
)


def get_current_organization():
    return getattr(_state, "organization", None)


def set_current_organization(organization):
    _state.organization = organization


def clear_current_organization():
    if hasattr(_state, "organization"):
        del _state.organization
    if hasattr(_state, "strict"):
        del _state.strict


def is_unscoped():
    """True when scoping is deliberately suspended (see `unscoped`)."""
    return getattr(_state, "unscoped", False)


def set_strict(strict):
    """Marks the current context as a web request.

    In strict mode a missing organization means *deny*, not *allow*. Outside
    it — management commands, migrations, the shell — a missing organization
    means the caller is operating platform-wide and queries run unfiltered.
    Without this distinction, a logged-in user whose organization failed to
    resolve would silently see every company's data.
    """
    _state.strict = bool(strict)


def is_strict():
    return getattr(_state, "strict", False)


class unscoped:
    """Context manager that suspends organization filtering.

    Needed for genuinely cross-organization work: platform administration,
    migrations, management commands and tests. Deliberately explicit and easy
    to grep for, so any use can be reviewed.

        with unscoped():
            Branch.objects.count()   # every organization
    """

    def __enter__(self):
        self._previous = getattr(_state, "unscoped", False)
        _state.unscoped = True
        return self

    def __exit__(self, *exc):
        _state.unscoped = self._previous
        return False


class OrganizationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    CLOSED = "CLOSED", _("Closed")


class SubscriptionPlan(models.TextChoices):
    """Manually assigned by platform staff for now — see Organization.plan.
    Real payment processing (a gateway charging a card or handling mobile
    money, webhooks confirming payment, automatic suspension on failure) is
    a distinct piece of work with its own provider decision to make first;
    this is the data model that work will hang off, not a replacement for it.
    """

    TRIAL = "TRIAL", _("Free Trial")
    BASIC = "BASIC", _("Basic")
    STANDARD = "STANDARD", _("Standard")
    PREMIUM = "PREMIUM", _("Premium")


class Organization(models.Model):
    """A pharmacy company. The top of the ownership tree.

    Everything a company owns — branches, staff, products, stock, sales,
    accounting — hangs off this. The platform-level product catalogue is the
    deliberate exception: it is shared reference data, not company data.
    """

    code = models.CharField(
        max_length=12, unique=True, editable=False, verbose_name=_("Organization Code"),
        help_text=_("Auto-generated, e.g. ORG-001."),
    )
    legal_name = models.CharField(
        max_length=200, verbose_name=_("Legal Name"),
        help_text=_("As registered. Appears on tax invoices and financial statements."),
    )
    trade_name = models.CharField(
        max_length=200, blank=True, verbose_name=_("Trade Name"),
        help_text=_("The name customers know. Falls back to the legal name."),
    )
    tin = models.CharField(max_length=32, blank=True, verbose_name=_("TIN"))
    license_number = models.CharField(
        max_length=80, blank=True, verbose_name=_("Licence Number")
    )
    phone = models.CharField(
        max_length=20, blank=True, validators=[phone_validator], verbose_name=_("Phone")
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    region = models.CharField(max_length=80, blank=True, verbose_name=_("Region"))
    city = models.CharField(max_length=80, blank=True, verbose_name=_("City"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    logo = models.ImageField(
        upload_to="organizations/", blank=True, null=True, verbose_name=_("Logo")
    )
    currency = models.CharField(
        max_length=8, default="ETB", verbose_name=_("Currency"),
        help_text=_("ISO code. Used on every money figure for this company."),
    )
    default_language = models.CharField(
        max_length=8, default="en", choices=[("en", _("English")), ("am", "አማርኛ")],
        verbose_name=_("Default Language"),
    )
    status = models.CharField(
        max_length=12, choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE, db_index=True, verbose_name=_("Status"),
        help_text=_("Suspended companies keep their data but cannot trade — "
                    "their staff are signed out immediately and can't log "
                    "back in until this changes."),
    )
    plan = models.CharField(
        max_length=12, choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.TRIAL, verbose_name=_("Plan"),
    )
    plan_notes = models.CharField(
        max_length=255, blank=True, verbose_name=_("Plan / Billing Notes"),
        help_text=_("Manual record until real payment processing exists — "
                    "e.g. \"Paid via bank transfer, receipt #1234, covers "
                    "Sep 2026.\""),
    )
    subscription_ends_at = models.DateField(
        null=True, blank=True, verbose_name=_("Subscription Ends"),
        help_text=_("When this pharmacy's current paid period ends. Leave "
                    "blank for an open-ended account."),
    )
    max_branches = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Branch Limit"),
        help_text=_("Optional cap tied to their plan. Leave blank for unlimited."),
    )
    max_users = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Staff Limit"),
        help_text=_("Optional cap tied to their plan. Leave blank for unlimited."),
    )
    is_platform_owner = models.BooleanField(
        default=False, verbose_name=_("Platform Owner"),
        help_text=_("Marks the organization that operates the platform itself. "
                    "There is at most one."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["legal_name"]

    def __str__(self):
        return self.trade_name or self.legal_name

    def get_absolute_url(self):
        return reverse("organizations:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"ORG-{self.pk:03d}"
            super().save(update_fields=["code"])

    @property
    def display_name(self):
        return self.trade_name or self.legal_name

    @property
    def is_active(self):
        return self.status == OrganizationStatus.ACTIVE

    @property
    def branch_count(self):
        from apps.branches.models import Branch

        with unscoped():
            return Branch.objects.filter(organization=self, is_active=True).count()

    @property
    def user_count(self):
        from apps.accounts.models import User

        with unscoped():
            return User.objects.filter(organization=self, is_active=True).count()

    @property
    def is_over_branch_limit(self):
        return self.max_branches is not None and self.branch_count >= self.max_branches

    @property
    def is_over_user_limit(self):
        return self.max_users is not None and self.user_count >= self.max_users


class PaymentProvider(models.TextChoices):
    """Where a payment record came from. MANUAL covers everything today —
    a bank transfer, cash, a mobile money screenshot someone checked by
    eye. Real gateways are reserved slots: adding one later means adding
    one more choice here and a webhook that calls `record_payment()`, not
    redesigning anything downstream."""

    MANUAL = "MANUAL", _("Manually recorded")
    CHAPA = "CHAPA", _("Chapa")


class PaymentStatus(models.TextChoices):
    SUCCESSFUL = "SUCCESSFUL", _("Successful")
    PENDING = "PENDING", _("Pending")
    FAILED = "FAILED", _("Failed")


class Payment(models.Model):
    """One payment toward an organization's subscription.

    Deliberately provider-agnostic. `provider` + `provider_reference` are
    generic enough that a future gateway integration is just another
    `provider` value with a real transaction id, populated by a webhook
    instead of a human typing a note — see `record_payment()` below, the
    single function both paths call.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="payments",
        verbose_name=_("Organization"),
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Amount"))
    currency = models.CharField(max_length=8, default="ETB", verbose_name=_("Currency"))
    provider = models.CharField(
        max_length=12, choices=PaymentProvider.choices, default=PaymentProvider.MANUAL,
        verbose_name=_("Provider"),
    )
    provider_reference = models.CharField(
        max_length=120, blank=True, verbose_name=_("Provider Reference"),
        help_text=_("A gateway's own transaction id, once one exists. Blank for "
                    "manually recorded payments."),
    )
    status = models.CharField(
        max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.SUCCESSFUL,
        verbose_name=_("Status"),
    )
    plan_at_payment = models.CharField(
        max_length=12, choices=SubscriptionPlan.choices, verbose_name=_("Plan Paid For"),
    )
    period_start = models.DateField(verbose_name=_("Period Start"))
    period_end = models.DateField(
        verbose_name=_("Period End"),
        help_text=_("The organization's subscription end date is set to this on "
                    "a successful payment."),
    )
    notes = models.CharField(
        max_length=255, blank=True, verbose_name=_("Notes"),
        help_text=_('E.g. "Bank transfer, receipt #1234" or "Telebirr screenshot '
                    'verified by Abebe".'),
    )
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("Recorded By"),
        help_text=_("Blank for a payment a gateway confirmed automatically."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization} — {self.amount} {self.currency} ({self.get_status_display()})"


def record_payment(*, organization, amount, period_end, plan=None,
                    provider=PaymentProvider.MANUAL, provider_reference="",
                    currency=None, period_start=None, notes="", recorded_by=None,
                    status=PaymentStatus.SUCCESSFUL):
    """The one place a payment takes effect. Everything else — the manual
    "Record Payment" screen today, a Chapa webhook once that integration
    exists — calls this and nothing else needs to know which one happened.

    On a SUCCESSFUL payment: extends the organization's subscription to
    `period_end`, updates the plan if one was paid for, and reactivates the
    organization if it had lapsed into suspension for non-payment. A
    PENDING or FAILED payment is still recorded (for the ledger and for a
    gateway's "payment failed" webhook) but changes nothing about the
    organization itself.
    """
    from datetime import date

    payment = Payment.objects.create(
        organization=organization, amount=amount, currency=currency or organization.currency,
        provider=provider, provider_reference=provider_reference, status=status,
        plan_at_payment=plan or organization.plan,
        period_start=period_start or date.today(), period_end=period_end,
        notes=notes, recorded_by=recorded_by,
    )
    if status == PaymentStatus.SUCCESSFUL:
        update_fields = ["subscription_ends_at", "status"]
        organization.subscription_ends_at = period_end
        if organization.status == OrganizationStatus.SUSPENDED:
            organization.status = OrganizationStatus.ACTIVE
        if plan:
            organization.plan = plan
            update_fields.append("plan")
        organization.save(update_fields=update_fields)
    return payment


class OrganizationQuerySet(models.QuerySet):
    def for_organization(self, organization):
        if organization is None:
            return self.none()
        return self.filter(organization=organization)

    def all_organizations(self):
        """Explicitly opts out of scoping. Greppable by design."""
        return self


class TenantManager(models.Manager.from_queryset(OrganizationQuerySet)):
    """Filters to the current organization unless scoping is suspended.

    Behaviour depends on context:

    * organization set            → filtered to it
    * no organization, web request → empty (fail closed)
    * no organization, command/shell → unfiltered (platform-wide)

    The middle case is the security-relevant one. The last keeps management
    commands and migrations working without tempting anyone to bypass the
    manager, which is the outcome this class exists to prevent.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_unscoped():
            return queryset
        organization = get_current_organization()
        if organization is not None:
            return queryset.filter(organization=organization)
        if is_strict():
            # A web request with no resolved organization gets nothing. Fail
            # closed: showing every company's data would be far worse than
            # showing an empty page.
            return queryset.none()
        return queryset


class OrganizationOwnedModel(models.Model):
    """Base for anything a pharmacy company owns.

    `objects` is scoped. `all_objects` is not, and is what platform-level
    code and migrations use.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="%(class)s_set",
        null=True, blank=True, db_index=True, verbose_name=_("Organization"),
        help_text=_("The pharmacy company that owns this record."),
    )

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    #: Nullable on purpose. Rows created before tenancy existed have no
    #: organization, and a non-null column would have required inventing one
    #: during the migration. `save()` fills it from the request, the data
    #: migration backfills existing rows, and `objects` filters strictly on a
    #: web request — so a null in practice only survives where no
    #: organization could legitimately apply.

    def save(self, *args, **kwargs):
        if self.organization_id is None:
            self.organization = self._infer_organization()
        super().save(*args, **kwargs)

    @staticmethod
    def _infer_organization():
        """Works out the owner when a caller did not supply one.

        Two safe sources, in order:

        1. The current request's organization.
        2. The only organization that exists — unambiguous by definition, and
           what keeps seeders, management commands and a single-company
           install working without every call site knowing about tenancy.

        When several organizations exist and there is no request, the owner is
        genuinely unknown, so this returns None rather than guessing. Guessing
        would attach one company's data to another, which is the exact failure
        tenancy exists to prevent.
        """
        current = get_current_organization()
        if current is not None:
            return current
        candidates = Organization.objects.all()[:2]
        if len(candidates) == 1:
            return candidates[0]
        return None
