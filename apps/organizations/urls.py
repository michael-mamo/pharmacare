from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("", views.OrganizationListView.as_view(), name="list"),
    path("add/", views.OrganizationCreateView.as_view(), name="create"),
    path("switch/", views.SwitchOrganizationView.as_view(), name="switch"),
    path("<int:pk>/", views.OrganizationDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.OrganizationUpdateView.as_view(), name="update"),
    path("<int:pk>/record-payment/", views.RecordPaymentView.as_view(), name="record_payment"),
]
