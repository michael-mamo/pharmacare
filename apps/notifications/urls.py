from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("refresh/", views.NotificationRefreshView.as_view(), name="refresh"),
    path("read/", views.NotificationMarkReadView.as_view(), name="mark_all_read"),
    path("read/<int:pk>/", views.NotificationMarkReadView.as_view(), name="mark_read"),
]
