"""
Audit log views — Administrator only, read-only.

There is deliberately no edit or delete view: an audit trail that can be
altered from the UI provides little assurance in a regulated environment.
"""
from django.views.generic import ListView

from apps.accounts.permissions import AdministratorRequiredMixin

from .models import AuditAction, AuditLog


class AuditLogListView(AdministratorRequiredMixin, ListView):
    model = AuditLog
    template_name = "audit/list.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user")
        action = self.request.GET.get("action")
        model_name = self.request.GET.get("model")
        query = self.request.GET.get("q")
        if action:
            qs = qs.filter(action=action)
        if model_name:
            qs = qs.filter(model_name=model_name)
        if query:
            qs = qs.filter(username__icontains=query) | qs.filter(object_repr__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["actions"] = AuditAction.choices
        context["model_names"] = (
            AuditLog.objects.exclude(model_name="")
            .values_list("model_name", flat=True)
            .distinct()
            .order_by("model_name")
        )
        return context
