"""
Branch context.

Every request that touches stock needs to know *which* branch it is acting
on. Rather than threading a branch argument through every view, this
middleware resolves it once and attaches it as `request.branch`.

How the active branch is decided
--------------------------------
1. A user assigned to a branch always gets that branch. It is not
   switchable — a Gondar cashier must not be able to sell Bole's stock, and
   this is enforced server-side, not by hiding a dropdown.
2. An Administrator (no fixed branch, or explicitly cleared) may switch. The
   choice is held in the session under `active_branch_id` and validated on
   every request, so revoking access or deactivating a branch takes effect
   immediately rather than at next login.
3. Failing both, the main branch is used, so a fresh install or a legacy
   account without a branch still works.

`request.branch` may be None only when no active branch exists at all (a
database with every branch deactivated). Views that write stock must handle
that; `require_branch` below does it for them.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _

SESSION_KEY = "active_branch_id"


class BranchContextMiddleware:
    """Attaches `request.branch` and `request.available_branches`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.branch = None
        request.available_branches = []

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            request.branch = self._resolve(request, user)
            # Only Administrators get a list to switch between; for everyone
            # else the switcher is not rendered at all.
            if user.can_access_all_branches():
                request.available_branches = list(user.accessible_branches())

        return self.get_response(request)

    def _resolve(self, request, user):
        from .models import Branch

        # A branch-assigned user is locked to it, whatever the session says.
        if user.branch_id and not user.can_access_all_branches():
            return user.branch if user.branch.is_active else None

        selected_id = request.session.get(SESSION_KEY)
        if selected_id:
            branch = Branch.objects.filter(pk=selected_id, is_active=True).first()
            # Re-validate every request: permissions or branch status may have
            # changed since the choice was made.
            if branch and user.may_use_branch(branch):
                return branch
            request.session.pop(SESSION_KEY, None)

        return user.default_branch()


def require_branch(view_func):
    """Guards a view that cannot function without an active branch.

    Used on anything that reads or writes stock. Without this, such a view
    would fail with an obscure error deep in the allocation code instead of
    telling the user what is actually wrong.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(request, "branch", None) is None:
            messages.error(
                request,
                _("No active branch is available for your account. Ask an "
                  "Administrator to assign you to a branch."),
            )
            return redirect("dashboard:landing")
        return view_func(request, *args, **kwargs)

    return _wrapped


class BranchRequiredMixin:
    """Class-based-view equivalent of `require_branch`."""

    def dispatch(self, request, *args, **kwargs):
        if getattr(request, "branch", None) is None:
            messages.error(
                request,
                _("No active branch is available for your account. Ask an "
                  "Administrator to assign you to a branch."),
            )
            return redirect("dashboard:landing")
        return super().dispatch(request, *args, **kwargs)


def branch_scope(queryset, request, field="branch"):
    """Restricts a queryset to what the current user may see.

    Administrators see the branch they have selected; everyone else sees only
    their own branch. Rows with no branch (recorded before multi-branch
    support) are included for Administrators so historical data is never
    hidden from the people responsible for it.
    """
    user = request.user
    branch = getattr(request, "branch", None)

    if not user.can_access_all_branches():
        if branch is None:
            return queryset.none()
        return queryset.filter(**{field: branch})

    if branch is None:
        return queryset
    from django.db.models import Q

    return queryset.filter(Q(**{field: branch}) | Q(**{f"{field}__isnull": True}))
