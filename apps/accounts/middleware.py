"""
Lightweight thread-local middleware that records the currently authenticated
user for the duration of a request. The Audit Log app (Phase 6) reads this
from model save/delete signals so every DB mutation can be attributed to a
user even in code paths that don't have direct access to `request`.
"""
import threading

_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


def get_current_ip():
    return getattr(_thread_locals, "ip", None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.ip = self._get_client_ip(request)
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.user = None
            _thread_locals.ip = None
        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class ForcePasswordChangeMiddleware:
    """Redirects any authenticated user with `force_password_change=True` to
    the mandatory password-change page, before they can reach anything else.

    Applies to newly created staff accounts and any account an Administrator
    has reset — a standard control for regulated environments where default
    or admin-issued passwords must not remain in use.

    Implementation note: `request.resolver_match` is not yet populated at
    this point in the middleware chain (URL resolution happens deeper,
    immediately before the view is invoked), so exemptions are computed
    from `reverse()`-resolved paths rather than resolver_match/url_name.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._exempt_paths = None

    def _get_exempt_paths(self):
        if self._exempt_paths is None:
            from django.urls import reverse

            self._exempt_paths = {
                reverse("accounts:force_password_change"),
                reverse("accounts:logout"),
            }
        return self._exempt_paths

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "force_password_change", False):
            is_exempt_path = request.path in self._get_exempt_paths()
            is_static_or_admin = request.path.startswith(("/static/", "/media/", "/admin/", "/i18n/"))
            if not is_exempt_path and not is_static_or_admin:
                from django.shortcuts import redirect

                return redirect("accounts:force_password_change")
        return self.get_response(request)
