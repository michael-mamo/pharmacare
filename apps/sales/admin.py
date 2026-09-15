from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("medicine_name", "unit_price", "line_total")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number", "customer", "payment_method", "status",
        "grand_total", "served_by", "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("invoice_number", "customer__name")
    readonly_fields = ("invoice_number", "voided_by", "voided_at")
    date_hierarchy = "created_at"
    inlines = [SaleItemInline]
