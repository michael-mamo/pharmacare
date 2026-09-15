"""
Signal handlers for the accounts app: records the client IP on every
successful login (visible to Administrators on the staff detail page, and
useful groundwork for the Phase 6 Audit Log).
"""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def record_last_login_ip(sender, request, user, **kwargs):
    ip = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = ip.split(",")[0].strip() if ip else request.META.get("REMOTE_ADDR")
    user.last_login_ip = ip
    user.save(update_fields=["last_login_ip"])
