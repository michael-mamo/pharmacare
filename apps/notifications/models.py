"""
Notification model.

Design notes
------------
- Notifications are **role-targeted**, not user-targeted, for operational
  alerts: a low-stock warning is relevant to whoever is on shift, not to one
  named person. `target_roles` holds a comma-separated role list; an empty
  value means "all staff". This avoids fanning out one row per user every
  time stock dips.
- `dedupe_key` prevents the same alert being recreated on every refresh.
  Without it, a nightly (or per-request) scan would pile up thousands of
  identical "Paracetamol is low" rows. The key encodes what the alert is
  *about*, so re-running the generator is idempotent.
- Read state is per user (`NotificationRead`), because a role-targeted
  notification has to be dismissable by each person independently.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    LOW_STOCK = "LOW_STOCK", _("Low Stock")
    EXPIRED = "EXPIRED", _("Expired Medicine")
    EXPIRING = "EXPIRING", _("Expiring Soon")
    NEW_PURCHASE = "NEW_PURCHASE", _("New Purchase")
    LARGE_SALE = "LARGE_SALE", _("Large Sale")
    PENDING_PAYMENT = "PENDING_PAYMENT", _("Pending Payment")
    SYSTEM = "SYSTEM", _("System")


class Severity(models.TextChoices):
    INFO = "INFO", _("Information")
    WARNING = "WARNING", _("Warning")
    CRITICAL = "CRITICAL", _("Critical")


class Notification(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications", verbose_name=_("Branch"),
        help_text=_("The branch this alert concerns. Blank means it applies "
                    "pharmacy-wide."),
    )
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices, db_index=True,
        verbose_name=_("Type"),
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.INFO,
        db_index=True, verbose_name=_("Severity"),
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    message = models.TextField(verbose_name=_("Message"))
    link = models.CharField(
        max_length=300, blank=True, verbose_name=_("Link"),
        help_text=_("Relative URL the notification points to, if any."),
    )
    target_roles = models.CharField(
        max_length=120, blank=True, verbose_name=_("Target Roles"),
        help_text=_("Comma-separated role codes. Blank means all staff."),
    )
    dedupe_key = models.CharField(
        max_length=200, unique=True, verbose_name=_("Deduplication Key"),
        help_text=_("Identifies what this alert is about, so refreshing "
                    "does not create duplicates."),
    )
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name=_("Active"),
        help_text=_("Cleared automatically when the underlying condition "
                    "no longer holds (e.g. stock was replenished)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Created"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Resolved"))

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    @property
    def roles_list(self):
        return [r.strip() for r in self.target_roles.split(",") if r.strip()]

    def is_for_user(self, user):
        """Administrators see everything; otherwise match the role list."""
        if user.is_administrator:
            return True
        roles = self.roles_list
        return not roles or user.role in roles

    def resolve(self):
        if self.is_active:
            self.is_active = False
            self.resolved_at = timezone.now()
            self.save(update_fields=["is_active", "resolved_at"])

    @property
    def badge_class(self):
        return {
            Severity.CRITICAL: "bg-danger-subtle text-danger",
            Severity.WARNING: "bg-warning-subtle text-warning-emphasis",
            Severity.INFO: "bg-light text-dark border",
        }.get(self.severity, "bg-light text-dark border")

    @property
    def icon(self):
        return {
            NotificationType.LOW_STOCK: "fa-triangle-exclamation",
            NotificationType.EXPIRED: "fa-calendar-xmark",
            NotificationType.EXPIRING: "fa-clock",
            NotificationType.NEW_PURCHASE: "fa-cart-shopping",
            NotificationType.LARGE_SALE: "fa-money-bill-trend-up",
            NotificationType.PENDING_PAYMENT: "fa-hourglass-half",
        }.get(self.notification_type, "fa-bell")


class NotificationRead(models.Model):
    """Per-user read marker. Separate from Notification because one
    role-targeted notification is read independently by each person."""

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_reads"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification Read Marker")
        verbose_name_plural = _("Notification Read Markers")
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"], name="unique_notification_read_per_user"
            )
        ]

    def __str__(self):
        return f"{self.user} read {self.notification_id}"
