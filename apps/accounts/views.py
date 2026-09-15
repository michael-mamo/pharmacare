"""
Authentication and staff-management views.

Uses Django's built-in auth views for login/logout/password-reset with
custom templates + forms (bootstrapped, on-brand), and Class-Based Views
for staff CRUD, restricted to Administrators via RoleRequiredMixin.
"""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormView

from .forms import (
    ForcedPasswordChangeForm,
    ProfileUpdateForm,
    StaffUserCreationForm,
    StaffUserUpdateForm,
    StyledAuthenticationForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from .models import Role, User
from .permissions import AdministratorRequiredMixin


class PharmaCareLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        # A suspended pharmacy (non-payment, closure, etc.) keeps its data
        # but cannot trade — that has to include its staff logging in, or
        # "suspended" is just a label nobody enforces. Platform staff are
        # exempt: they have no organization of their own to be suspended.
        organization = getattr(user, "organization", None)
        if organization is not None and not organization.is_active:
            messages.error(
                self.request,
                "This pharmacy's account is currently suspended. Contact "
                "your platform administrator to resolve this.",
            )
            return self.form_invalid(form)
        messages.success(self.request, f"Welcome back, {user.get_full_name() or user.username}!")
        return super().form_valid(form)


class PharmaCareLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("accounts:login")


# ---------------------------------------------------------------------------
# Password reset (Django's built-in token-based flow, restyled)
# ---------------------------------------------------------------------------
class PharmaCarePasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")


class PharmaCarePasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PharmaCarePasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class PharmaCarePasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class ForcePasswordChangeView(LoginRequiredMixin, FormView):
    """Mandatory password-change screen shown to any user whose account has
    `force_password_change=True` — enforced globally by
    ForcePasswordChangeMiddleware, not just linked from the menu."""

    template_name = "accounts/force_password_change.html"
    form_class = ForcedPasswordChangeForm
    success_url = reverse_lazy("dashboard:landing")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.force_password_change:
            return redirect_to_dashboard()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)  # keep the user logged in
        messages.success(self.request, "Your password has been updated.")
        return super().form_valid(form)


def redirect_to_dashboard():
    from django.shortcuts import redirect

    return redirect("dashboard:landing")


# ---------------------------------------------------------------------------
# Staff (User) management — Administrator only
# ---------------------------------------------------------------------------
class OrganizationStaffQuerysetMixin:
    """Scopes User queries to the current pharmacy, for every staff view.

    Without this, `User.objects.all()` — the Django default a bare
    `model = User` falls back to — spans every organization on the
    platform, because User isn't an OrganizationOwnedModel subclass (it
    can't be: it's what organization membership is defined *on*). Left
    unscoped, any pharmacy Administrator could browse, edit or delete any
    other pharmacy's staff by URL, or even reach a System Administrator
    account, just by guessing or incrementing an id — a real, severe gap,
    not a theoretical one.

    Filtering on organization alone would exclude platform staff too, in
    principle — their organization is always None, which never equals a
    real pharmacy's own. In practice that relies on `request.organization`
    itself always being correctly populated, and a data inconsistency
    (a pharmacy user whose own organization ended up null, from a bad
    import or a bug elsewhere) would silently reopen exactly this hole:
    filtering by organization=None would then match every other null-
    organization user, platform staff included. So this excludes platform
    staff explicitly too, unconditionally — a second, independent gate
    that holds even if the first one's data assumption doesn't.
    """

    def get_queryset(self):
        return User.objects.filter(
            organization=self.request.organization
        ).exclude(role=Role.SYSTEM_ADMIN)


class StaffListView(OrganizationStaffQuerysetMixin, AdministratorRequiredMixin, ListView):
    model = User
    template_name = "accounts/staff_list.html"
    context_object_name = "staff_members"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by("first_name", "last_name")
        query = self.request.GET.get("q")
        role = self.request.GET.get("role")
        if query:
            qs = qs.filter(username__icontains=query) | qs.filter(email__icontains=query)
        if role:
            qs = qs.filter(role=role)
        return qs


class StaffDetailView(OrganizationStaffQuerysetMixin, AdministratorRequiredMixin, DetailView):
    model = User
    template_name = "accounts/staff_detail.html"
    context_object_name = "staff_member"


class StaffCreateView(AdministratorRequiredMixin, CreateView):
    model = User
    form_class = StaffUserCreationForm
    template_name = "accounts/staff_form.html"
    success_url = reverse_lazy("accounts:staff_list")

    def dispatch(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is not None and org.is_over_user_limit:
            messages.error(request, (
                f"You've reached your plan's staff limit ({org.max_users}). "
                "Contact your platform administrator to raise it."
            ))
            return redirect("accounts:staff_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Staff account created successfully.")
        return super().form_valid(form)


class StaffUpdateView(OrganizationStaffQuerysetMixin, AdministratorRequiredMixin, UpdateView):
    model = User
    form_class = StaffUserUpdateForm
    template_name = "accounts/staff_form.html"
    success_url = reverse_lazy("accounts:staff_list")

    def form_valid(self, form):
        messages.success(self.request, "Staff account updated successfully.")
        return super().form_valid(form)


class StaffDeleteView(OrganizationStaffQuerysetMixin, AdministratorRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/staff_confirm_delete.html"
    success_url = reverse_lazy("accounts:staff_list")

    def form_valid(self, form):
        messages.success(self.request, "Staff account deleted.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Self-service profile
# ---------------------------------------------------------------------------
class ProfileUpdateView(LoginRequiredMixin, FormView):
    template_name = "accounts/profile.html"
    form_class = ProfileUpdateForm
    success_url = reverse_lazy("accounts:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)
