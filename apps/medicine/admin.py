from django.contrib import admin

from .models import Category, Medicine


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "medicine_count", "created_at")
    search_fields = ("name",)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "category", "supplier", "quantity", "reorder_level",
        "expiry_date", "selling_price", "is_active",
    )
    list_filter = ("category", "supplier", "is_active", "unit")
    search_fields = ("code", "name", "generic_name", "brand", "barcode")
    readonly_fields = ("code",)
    date_hierarchy = "expiry_date"
