from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    # POS terminal
    path("pos/", views.POSView.as_view(), name="pos"),
    path("pos/lookup/", views.medicine_lookup, name="medicine_lookup"),
    path("pos/checkout/", views.pos_checkout, name="pos_checkout"),
    # Sales history & invoices
    path("", views.SaleListView.as_view(), name="sale_list"),
    path("<int:pk>/", views.SaleDetailView.as_view(), name="sale_detail"),
    path("<int:pk>/invoice/", views.SaleInvoiceView.as_view(), name="sale_invoice"),
    path("<int:pk>/void/", views.sale_void, name="sale_void"),
]
