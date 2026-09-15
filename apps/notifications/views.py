"""
Notification views. Every role sees notifications, but only the ones
targeted at their role (see Notification.is_for_user).
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView, View

from .models import Notification, NotificationRead
from .services import refresh_notifications, unread_for_user


class NotificationListView(LoginRequiredMixin, TemplateView):
    template_name = "notifications/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        show = self.request.GET.get("show", "unread")

        qs = Notification.objects.filter(is_active=True).select_related("branch")
        if show == "all":
            qs = Notification.objects.all().select_related("branch")
        visible = [n for n in qs if n.is_for_user(user)]
        # Branch scoping: staff see their own branch's alerts plus any
        # pharmacy-wide ones; Administrators see the active branch's.
        branch = getattr(self.request, "branch", None)
        if not user.can_access_all_branches():
            allowed = {user.branch_id} if user.branch_id else set()
            visible = [n for n in visible if n.branch_id is None or n.branch_id in allowed]
        elif branch is not None:
            visible = [n for n in visible if n.branch_id in (None, branch.pk)]

        read_ids = set(
            NotificationRead.objects.filter(user=user).values_list("notification_id", flat=True)
        )
        if show == "unread":
            visible = [n for n in visible if n.pk not in read_ids]

        context["notifications"] = visible
        context["read_ids"] = read_ids
        context["show"] = show
        context["unread_count"] = len(
            unread_for_user(user, branch=getattr(self.request, "branch", None))
        )
        return context


class NotificationRefreshView(LoginRequiredMixin, View):
    """Manual rescan. Also available as `manage.py refresh_notifications`
    for scheduling via Task Scheduler / cron."""

    def post(self, request):
        result = refresh_notifications()
        messages.success(
            request,
            f"Notifications refreshed — {result['active']} active, "
            f"{result['resolved']} resolved.",
        )
        return redirect("notifications:list")


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk=None):
        user = request.user
        if pk:
            targets = Notification.objects.filter(pk=pk)
        else:
            targets = [n for n in unread_for_user(
                user, branch=getattr(request, "branch", None))]
        for notification in targets:
            if notification.is_for_user(user):
                NotificationRead.objects.get_or_create(notification=notification, user=user)
        return redirect(request.META.get("HTTP_REFERER") or "notifications:list")
