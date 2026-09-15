from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "status", "medicine_count")
    list_filter = ("status",)
    search_fields = ("name", "contact_person", "phone", "email")
