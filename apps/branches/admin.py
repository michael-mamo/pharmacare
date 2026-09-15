from django.contrib import admin

from .models import Branch, BranchStock


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "is_main", "is_active", "manager")
    list_filter = ("is_active", "is_main", "city")
    search_fields = ("name", "code", "city")
    readonly_fields = ("code",)


@admin.register(BranchStock)
class BranchStockAdmin(admin.ModelAdmin):
    list_display = ("medicine", "branch", "quantity", "reorder_level", "updated_at")
    list_filter = ("branch",)
    search_fields = ("medicine__name", "medicine__code")
    autocomplete_fields = ()
