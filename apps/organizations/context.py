"""
Resolving the current organization for a request.

A user belongs to exactly one organization, so the organization is derived
from the authenticated user — never from a URL, a form field or a header.
That is the whole point: if it could be supplied by the client, it could be
forged, and tenancy would be advisory rather than enforced.

Platform staff (system administrators) belong to no organization. They may
act inside one explicitly, and that choice is held in the session and
re-validated on every request.
"""
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

from apps.organizations.models import (
    Organization, OrganizationStatus, clear_current_organization,
    set_current_organization, set_strict,
)

SESSION_KEY = "active_organization_id"


class OrganizationContextMiddleware:
    """Sets the current organization for the duration of the request.

    Must run after AuthenticationMiddleware (it needs request.user) and
    before BranchContextMiddleware (branches are scoped to an organization).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        organization = None
        user = getattr(request, "user", None)

        if user is not None and user.is_authenticated:
            if getattr(user, "organization_id", None):
                organization = user.organization
                # A suspended (non-payment, closure, etc.) pharmacy stops
                # trading immediately, not just at next login — otherwise
                # "suspended" only ever meant "can't log back in", and
                # anyone already signed in would keep working regardless.
                if not organization.is_active and not request.path.startswith("/accounts/logout/"):
                    logout(request)
                    messages.error(
                        request,
                        "This pharmacy's account has been suspended. Contact "
                        "your platform administrator to resolve this.",
                    )
                    return redirect(reverse("accounts:login"))
            elif getattr(user, "is_platform_staff", lambda: False)():
                organization = self._session_organization(request)

        request.organization = organization
        set_current_organization(organization)
        # Strict for the duration of the request: no organization means no
        # data, rather than everyone's data.
        set_strict(user is not None and user.is_authenticated)
        try:
            response = self.get_response(request)
        finally:
            # Always clear: the thread or task is reused, and a leaked
            # organization would scope the next request to the wrong company.
            clear_current_organization()
            request.organization = organization
        return response

    @staticmethod
    def _session_organization(request):
        organization_id = request.session.get(SESSION_KEY)
        if not organization_id:
            return None
        # Organization has no tenant scoping of its own (it's the thing
        # scoping happens relative to), so the plain manager already sees
        # every company — there's no separate "all_objects" here the way
        # there is on OrganizationOwnedModel subclasses.
        return Organization.objects.filter(
            pk=organization_id, status=OrganizationStatus.ACTIVE
        ).first()
