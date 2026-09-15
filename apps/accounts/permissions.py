"""
Central place for role-based access control (RBAC) helpers.

Two flavours are provided so both function-based and class-based views
(the project uses CBVs wherever appropriate, per spec) can enforce roles
with one line:

    Function-based view:
        @role_required("ADMIN", "STORE_MANAGER")
        def my_view(request): ...

    Class-based view:
        class MyView(RoleRequiredMixin, ListView):
            allowed_roles = ["ADMIN", "STORE_MANAGER"]
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    """Function-based view decorator restricting access to the given roles.
    Superusers and Administrators always pass."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            user = request.user
            if user.is_administrator or user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that page.")
            raise PermissionDenied("Insufficient role privileges.")

        return _wrapped

    return decorator


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Class-based view mixin. Set `allowed_roles = ["ADMIN", ...]` on the
    view. Administrators and superusers always pass regardless of the list.
    """

    allowed_roles = []
    permission_denied_message = "You do not have permission to access that page."
    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_administrator:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()


class AdministratorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["ADMIN"]


class PlatformStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to platform staff (System Administrator) only.

    Deliberately does NOT reuse RoleRequiredMixin's "Administrators always
    pass" rule. A pharmacy Administrator has full power inside their own
    company and none outside it — that boundary is the whole point of
    platform staff being a distinct role, not a bigger version of
    Administrator. Use this for screens no pharmacy should reach: the
    shared standard catalogue, and managing organizations themselves.
    """

    permission_denied_message = "This area is for platform administrators only."
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_platform_staff()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()
