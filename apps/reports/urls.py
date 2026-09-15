from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportIndexView.as_view(), name="index"),
    path("<slug:slug>/", views.ReportDetailView.as_view(), name="detail"),
    path("<slug:slug>/export/<str:fmt>/", views.ReportExportView.as_view(), name="export"),
]
