from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.PharmaCareLoginView.as_view(), name="login"),
    path("logout/", views.PharmaCareLogoutView.as_view(), name="logout"),
    # Password reset
    path("password-reset/", views.PharmaCarePasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.PharmaCarePasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        views.PharmaCarePasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.PharmaCarePasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    # Profile (self-service)
    path("profile/", views.ProfileUpdateView.as_view(), name="profile"),
    path("password-change-required/", views.ForcePasswordChangeView.as_view(), name="force_password_change"),
    # Staff management (Administrator only)
    path("staff/", views.StaffListView.as_view(), name="staff_list"),
    path("staff/add/", views.StaffCreateView.as_view(), name="staff_create"),
    path("staff/<int:pk>/", views.StaffDetailView.as_view(), name="user_detail"),
    path("staff/<int:pk>/edit/", views.StaffUpdateView.as_view(), name="staff_update"),
    path("staff/<int:pk>/delete/", views.StaffDeleteView.as_view(), name="staff_delete"),
]
