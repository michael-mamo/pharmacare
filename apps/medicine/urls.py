from django.urls import path

from . import views

app_name = "medicine"

urlpatterns = [
    # Medicines
    path("", views.MedicineListView.as_view(), name="medicine_list"),
    path("add/", views.MedicineCreateView.as_view(), name="medicine_create"),
    path("<int:pk>/", views.MedicineDetailView.as_view(), name="medicine_detail"),
    path("<int:pk>/edit/", views.MedicineUpdateView.as_view(), name="medicine_update"),
    path("<int:pk>/delete/", views.MedicineDeleteView.as_view(), name="medicine_delete"),
    path("<int:pk>/label/", views.MedicineLabelView.as_view(), name="medicine_label"),
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
]
