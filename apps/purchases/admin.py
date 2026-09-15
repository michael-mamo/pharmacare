from django.contrib import admin

from .models import PurchaseInvoice, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("purchase_number", "supplier", "purchase_date", "total_amount", "recorded_by")
    list_filter = ("supplier", "purchase_date")
    search_fields = ("purchase_number", "supplier__name")
    readonly_fields = ("purchase_number",)
    inlines = [PurchaseItemInline]
