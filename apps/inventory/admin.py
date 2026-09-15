from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "medicine", "movement_type", "quantity_before", "quantity_after",
        "performed_by", "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("medicine__name", "reason", "destination")
    readonly_fields = ("quantity_before", "quantity_after")


from .stocktake import StockLedger, StockTake, StockTakeLine  # noqa: E402


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ("created_at", "branch", "medicine", "source",
                    "quantity_change", "balance_after", "reference", "performed_by")
    list_filter = ("source", "branch", "created_at")
    search_fields = ("medicine__name", "reference")
    date_hierarchy = "created_at"

    # Append-only, here as well as in the UI.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StockTakeLineInline(admin.TabularInline):
    model = StockTakeLine
    extra = 0
    readonly_fields = ("medicine", "expected_quantity")


@admin.register(StockTake)
class StockTakeAdmin(admin.ModelAdmin):
    list_display = ("reference", "branch", "category", "status",
                    "counted_lines", "total_lines", "started_by", "started_at")
    list_filter = ("status", "branch")
    readonly_fields = ("reference", "started_at", "posted_at")
    inlines = [StockTakeLineInline]
