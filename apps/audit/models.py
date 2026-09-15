"""
Audit log.

Records who changed what, when, and from which IP — the four fields the
spec calls for. Entries are written by signal handlers (see signals.py)
using the thread-local user/IP captured by
`apps.accounts.middleware.CurrentUserMiddleware`, which was wired in
during Phase 1 precisely so this app wouldn't need to thread `request`
through every model method.

The log is append-only by design: no edit or delete views exist, and it is
readable by Administrators only. A log that ordinary users can alter is
worth very little in a regulated environment.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditAction(models.TextChoices):
    CREATE = "CREATE", _("Created")
    UPDATE = "UPDATE", _("Updated")
    DELETE = "DELETE", _("Deleted")
    LOGIN = "LOGIN", _("Logged in")
    LOGOUT = "LOGOUT", _("Logged out")
    LOGIN_FAILED = "LOGIN_FAILED", _("Failed login")


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_entries", verbose_name=_("User"),
    )
    # Kept as text as well as FK: if a staff account is deleted the FK nulls
    # out, but the audit trail must still say who did it.
    username = models.CharField(max_length=150, blank=True, verbose_name=_("Username"))
    action = models.CharField(
        max_length=15, choices=AuditAction.choices, db_index=True, verbose_name=_("Action")
    )
    model_name = models.CharField(max_length=100, blank=True, db_index=True, verbose_name=_("Record Type"))
    object_id = models.CharField(max_length=50, blank=True, verbose_name=_("Record ID"))
    object_repr = models.CharField(max_length=300, blank=True, verbose_name=_("Record"))
    changes = models.TextField(blank=True, verbose_name=_("Details"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Date"))

    class Meta:
        verbose_name = _("Audit Log Entry")
        verbose_name_plural = _("Audit Log")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["model_name"]),
        ]

    def __str__(self):
        who = self.username or _("system")
        return f"{who} {self.get_action_display()} {self.object_repr or self.model_name}"

    @property
    def badge_class(self):
        return {
            AuditAction.CREATE: "bg-success-subtle text-success",
            AuditAction.UPDATE: "bg-warning-subtle text-warning-emphasis",
            AuditAction.DELETE: "bg-danger-subtle text-danger",
            AuditAction.LOGIN: "bg-light text-dark border",
            AuditAction.LOGOUT: "bg-light text-dark border",
            AuditAction.LOGIN_FAILED: "bg-danger-subtle text-danger",
        }.get(self.action, "bg-light text-dark border")
