from django.urls import path

from .views import DashboardHomeView, RoleLandingView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    # Role-aware landing: used for LOGIN_REDIRECT_URL and the site root.
    path("go/", RoleLandingView.as_view(), name="landing"),
]
