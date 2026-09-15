from django.contrib import admin

from .models import CatalogueCategory, CatalogueProduct


@admin.register(CatalogueCategory)
class CatalogueCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order")
    search_fields = ("name", "code")


@admin.register(CatalogueProduct)
class CatalogueProductAdmin(admin.ModelAdmin):
    list_display = ("display_name", "atc_code", "schedule", "data_source",
                    "is_essential", "is_active")
    list_filter = ("schedule", "dosage_form", "data_source", "is_essential",
                   "requires_cold_chain", "is_active")
    search_fields = ("generic_name", "brand_name", "atc_code",
                     "efda_registration_number", "barcode")
