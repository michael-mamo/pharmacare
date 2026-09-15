from django.urls import path

from . import views

app_name = "catalogue"

urlpatterns = [
    path("", views.CatalogueListView.as_view(), name="product_list"),
    path("_seed/", views.SeedCatalogueTriggerView.as_view(), name="seed_trigger"),
    path("add/", views.CatalogueProductCreateView.as_view(), name="product_create"),
    path("<int:pk>/", views.CatalogueDetailView.as_view(), name="product_detail"),
    path("<int:pk>/register/", views.RegisterProductView.as_view(), name="register"),
]
