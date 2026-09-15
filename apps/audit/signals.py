"""
Signal handlers that populate the audit log.

Rather than sprinkling audit calls through every view, we listen to
post_save / post_delete on an explicit allow-list of business models, plus
Django's auth signals for login/logout/failed-login. The acting user and IP
come from `apps.accounts.middleware.CurrentUserMiddleware`.

Why an allow-list rather than every model: logging Session, AccessAttempt,
NotificationRead and similar churn would bury the entries that matter, and
audit noise is functionally the same as no audit at all.
"""
import logging

from django.contrib.auth import user_logged_in, user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.middleware import get_current_ip, get_current_user

from .models import AuditAction, AuditLog

logger = logging.getLogger(__name__)

#: "app_label.ModelName" of everything worth auditing.
AUDITED_MODELS = {
    "accounts.User",
    "medicine.Medicine",
    "medicine.Category",
    "suppliers.Supplier",
    "customers.Customer",
    "purchases.PurchaseInvoice",
    "purchases.PurchaseItem",
    "inventory.StockMovement",
    "sales.Sale",
    "settings_app.PharmacySettings",
}


def _label(instance):
    meta = instance._meta
    return f"{meta.app_label}.{meta.object_name}"


def _write(action, instance=None, extra=""):
    """Never let an audit failure break the operation being audited."""
    try:
        user = get_current_user()
        authenticated = bool(user and getattr(user, "is_authenticated", False))
        AuditLog.objects.create(
            user=user if authenticated else None,
            username=(user.username if authenticated else ""),
            action=action,
            model_name=_label(instance) if instance is not None else "",
            object_id=str(getattr(instance, "pk", "") or ""),
            object_repr=(str(instance)[:300] if instance is not None else ""),
            changes=extra,
            ip_address=get_current_ip(),
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to write audit log entry")


@receiver(post_save)
def audit_save(sender, instance, created, **kwargs):
    if _label(instance) not in AUDITED_MODELS:
        return
    _write(AuditAction.CREATE if created else AuditAction.UPDATE, instance)


@receiver(post_delete)
def audit_delete(sender, instance, **kwargs):
    if _label(instance) not in AUDITED_MODELS:
        return
    _write(AuditAction.DELETE, instance)


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    try:
        AuditLog.objects.create(
            user=user, username=user.username, action=AuditAction.LOGIN,
            ip_address=get_current_ip(),
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to write login audit entry")


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if user is None:
        return
    try:
        AuditLog.objects.create(
            user=user, username=user.username, action=AuditAction.LOGOUT,
            ip_address=get_current_ip(),
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to write logout audit entry")


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, **kwargs):
    """Failed logins matter more than successful ones for spotting an attack.
    Only the attempted username is stored — never the submitted password."""
    try:
        AuditLog.objects.create(
            user=None,
            username=str(credentials.get("username", ""))[:150],
            action=AuditAction.LOGIN_FAILED,
            ip_address=get_current_ip(),
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to write failed-login audit entry")
