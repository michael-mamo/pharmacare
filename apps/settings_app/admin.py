from django.contrib import admin

from .models import PharmacySettings


@admin.register(PharmacySettings)
class PharmacySettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "currency", "tax_rate", "invoice_prefix", "updated_at")

    # Singleton: never allow a second row, and never allow deleting the only one.
    def has_add_permission(self, request):
        return not PharmacySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
