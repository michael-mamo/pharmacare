from django.contrib import admin

from .models import Notification, NotificationRead


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "notification_type", "severity", "is_active", "created_at")
    list_filter = ("notification_type", "severity", "is_active")
    search_fields = ("title", "message", "dedupe_key")
    readonly_fields = ("dedupe_key", "created_at", "resolved_at")


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("notification", "user", "read_at")
