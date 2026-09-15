"""
Makes pharmacy branding available in every template (navbar, sidebar, login
page, invoices, etc.) without every view having to pass it explicitly.

Each pharmacy has its own settings row (see PharmacySettings) — this reads
whichever one matches `request.organization`, so two different pharmacies
never show each other's name, logo or invoice details. Platform staff
browsing platform-wide screens (no organization selected) see a generic
platform label instead of any one pharmacy's own branding — showing a
specific pharmacy's name there would be actively misleading, not just
incomplete.
"""
from decouple import config

from django.conf import settings


def _env_defaults():
    return {
        "PHARMACY_NAME": config("PHARMACY_PLATFORM_NAME", default="PharmaCare"),
        "PHARMACY_CURRENCY": config("PHARMACY_CURRENCY", default="ETB"),
        "PHARMACY_TAX_RATE": config("PHARMACY_TAX_RATE", default="15", cast=str),
        "PHARMACY_INVOICE_PREFIX": config("PHARMACY_INVOICE_PREFIX", default="INV-"),
        "PHARMACY_LOGO_URL": "",
        "PHARMACY_INVOICE_FOOTER": "",
        "PHARMACY_SETTINGS": None,
    }


def pharmacy_settings(request):
    data = _env_defaults()
    organization = getattr(request, "organization", None)
    if organization is None:
        # No specific pharmacy in view — either logged out, or platform
        # staff who haven't switched into one. Generic platform branding
        # only; never fall back to some other pharmacy's settings.
        return data
    try:
        from apps.settings_app.models import PharmacySettings

        conf = PharmacySettings.load(organization)
        data.update({
            "PHARMACY_NAME": conf.name or organization.display_name,
            "PHARMACY_CURRENCY": conf.currency or data["PHARMACY_CURRENCY"],
            "PHARMACY_TAX_RATE": str(conf.tax_rate),
            "PHARMACY_INVOICE_PREFIX": conf.invoice_prefix or data["PHARMACY_INVOICE_PREFIX"],
            "PHARMACY_LOGO_URL": conf.logo.url if conf.logo else "",
            "PHARMACY_INVOICE_FOOTER": conf.invoice_footer or "",
            "PHARMACY_SETTINGS": conf,
        })
    except Exception:
        # Before the first migration (or during one) the table may not exist
        # yet — fall back to env values rather than 500 on every page.
        pass

    # Branch context for the navbar switcher. request.branch itself is set by
    # BranchContextMiddleware; this just exposes the switchable list.
    data["available_branches"] = getattr(request, "available_branches", [])
    data["BRAND_COLORS"] = settings.BRAND_COLORS
    data["ACTIVE_THEME"] = request.COOKIES.get("pharmacare_theme", "light")

    # Unread notification count for the navbar bell.
    data["UNREAD_NOTIFICATIONS"] = []
    data["UNREAD_NOTIFICATION_COUNT"] = 0
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        try:
            from apps.notifications.services import unread_for_user

            unread = unread_for_user(user, branch=getattr(request, "branch", None))
            data["UNREAD_NOTIFICATIONS"] = unread[:6]
            data["UNREAD_NOTIFICATION_COUNT"] = len(unread)
        except Exception:
            pass
    return data
