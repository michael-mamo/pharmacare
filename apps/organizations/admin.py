from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("code", "legal_name", "trade_name", "city", "status",
                    "branch_count", "user_count", "created_at")
    list_filter = ("status", "region", "city")
    search_fields = ("code", "legal_name", "trade_name", "tin")
    readonly_fields = ("code", "created_at")
