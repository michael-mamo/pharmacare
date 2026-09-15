from django.urls import path

from . import views

app_name = "branches"

urlpatterns = [
    path("", views.BranchListView.as_view(), name="branch_list"),
    path("add/", views.BranchCreateView.as_view(), name="branch_create"),
    path("switch/", views.SwitchBranchView.as_view(), name="switch"),
    path("stock/", views.BranchStockListView.as_view(), name="stock"),
    path("compare/", views.BranchComparisonView.as_view(), name="compare"),
    path("transfer/", views.TransferCreateView.as_view(), name="transfer"),
    path("<int:pk>/", views.BranchDetailView.as_view(), name="branch_detail"),
    path("<int:pk>/edit/", views.BranchUpdateView.as_view(), name="branch_update"),
]
