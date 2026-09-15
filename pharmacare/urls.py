"""
Root URL configuration for the PharmaCare Management System.

Each domain app owns its own urls.py (included with a namespace) so the
project scales cleanly as Phases 2-6 add new apps — this file only ever
needs one new `include()` line per phase.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # language switcher (set_language)
    path("", RedirectView.as_view(pattern_name="dashboard:landing", permanent=False)),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("medicines/", include("apps.medicine.urls", namespace="medicine")),
    path("customers/", include("apps.customers.urls", namespace="customers")),
    path("suppliers/", include("apps.suppliers.urls", namespace="suppliers")),
    path("purchases/", include("apps.purchases.urls", namespace="purchases")),
    path("inventory/", include("apps.inventory.urls", namespace="inventory")),
    path("sales/", include("apps.sales.urls", namespace="sales")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("audit/", include("apps.audit.urls", namespace="audit")),
    path("catalogue/", include("apps.catalogue.urls", namespace="catalogue")),
    path("branches/", include("apps.branches.urls", namespace="branches")),
    path("organizations/", include("apps.organizations.urls", namespace="organizations")),
    path("settings/", include("apps.settings_app.urls", namespace="settings_app")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
