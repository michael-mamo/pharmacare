from django.contrib import admin

from .fiscal import FiscalYear, FiscalYearSettings


@admin.register(FiscalYearSettings)
class FiscalYearSettingsAdmin(admin.ModelAdmin):
    list_display = ("calendar_system", "start_label", "display_calendar", "updated_at")

    def has_add_permission(self, request):
        # Singleton: the row is created on first load.
        return not FiscalYearSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("label", "start_date", "end_date", "status",
                    "calendar_system", "closed_at")
    list_filter = ("status", "calendar_system")
    readonly_fields = ("closed_at", "closed_by")
