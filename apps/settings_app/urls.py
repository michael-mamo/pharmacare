from django.urls import path

from . import views

app_name = "settings_app"

urlpatterns = [
    path("", views.PharmacySettingsUpdateView.as_view(), name="settings"),
    path("backup/", views.DatabaseBackupView.as_view(), name="backup"),
]
