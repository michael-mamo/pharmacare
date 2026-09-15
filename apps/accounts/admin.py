from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PharmaCareUserAdmin(UserAdmin):
    """Extends Django's UserAdmin with PharmaCare's role & contact fields."""

    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "is_active_employee",
        "is_staff",
        "date_joined_pharmacy",
    )
    list_filter = ("role", "is_active_employee", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("-date_joined_pharmacy",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "PharmaCare Profile",
            {"fields": ("role", "phone_number", "profile_image", "is_active_employee")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "PharmaCare Profile",
            {"fields": ("role", "phone_number", "email", "is_active_employee")},
        ),
    )
