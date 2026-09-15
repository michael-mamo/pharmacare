"""
Organization (pharmacy tenant) management views.

Platform-only, throughout — same reasoning as the catalogue: a pharmacy
Administrator runs their own company and has no business seeing another
one, or even that others exist. Only platform staff (System Administrator)
reach anything here.
"""
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import PlatformStaffRequiredMixin
from apps.organizations.context import SESSION_KEY

from .forms import OrganizationForm, RecordPaymentForm
from .models import Organization, OrganizationStatus, PaymentProvider, record_payment, unscoped


class OrganizationListView(PlatformStaffRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/organization_list.html"
    context_object_name = "organizations"
    paginate_by = 30

    def get_queryset(self):
        with unscoped():
            qs = Organization.objects.order_by("legal_name")
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            qs = (qs.filter(legal_name__icontains=query)
                  | qs.filter(trade_name__icontains=query)
                  | qs.filter(code__icontains=query))
        if status:
            qs = qs.filter(status=status)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = OrganizationStatus.choices
        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
        }
        with unscoped():
            context["active_organization_id"] = self.request.session.get(SESSION_KEY)
        return context


class OrganizationCreateView(PlatformStaffRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/organization_form.html"

    def form_valid(self, form):
        messages.success(self.request, _(
            "%(name)s created. Switch into it to add its first branch and "
            "staff account."
        ) % {"name": form.instance.display_name or form.instance.legal_name})
        return super().form_valid(form)


class OrganizationDetailView(PlatformStaffRequiredMixin, DetailView):
    model = Organization
    template_name = "organizations/organization_detail.html"
    context_object_name = "organization"

    def get_queryset(self):
        with unscoped():
            return Organization.objects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with unscoped():
            context["active_organization_id"] = self.request.session.get(SESSION_KEY)
        return context


class OrganizationUpdateView(PlatformStaffRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/organization_form.html"

    def get_queryset(self):
        with unscoped():
            return Organization.objects

    def form_valid(self, form):
        messages.success(self.request, _("%(name)s updated.") % {
            "name": form.instance.display_name or form.instance.legal_name
        })
        return super().form_valid(form)


class SwitchOrganizationView(PlatformStaffRequiredMixin, View):
    """Lets platform staff act inside one pharmacy's data at a time.

    Mirrors branches:switch — same idea, one level up. Only ACTIVE
    organizations can be entered; a suspended one keeps its data visible
    in the platform list but is not somewhere platform staff work "as".
    """

    def post(self, request):
        org_id = request.POST.get("organization")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

        if not org_id:
            request.session.pop(SESSION_KEY, None)
            messages.success(request, _("Back to the platform view — no pharmacy selected."))
            return redirect(next_url)

        with unscoped():
            organization = Organization.objects.filter(
                pk=org_id, status=OrganizationStatus.ACTIVE
            ).first()
        if organization is None:
            messages.error(request, _("That pharmacy isn't available to switch into."))
            return redirect(next_url)

        request.session[SESSION_KEY] = organization.pk
        messages.success(request, _("Now working inside %(name)s.") % {
            "name": organization.display_name
        })
        return redirect(next_url)


class RecordPaymentView(PlatformStaffRequiredMixin, View):
    """Manually logs a payment against a pharmacy's subscription.

    This is the whole billing workflow that exists today — no gateway, no
    webhook, just a platform staff member confirming money arrived (bank
    transfer, cash, a Telebirr screenshot) and extending the subscription
    accordingly. It calls the exact same `record_payment()` a future
    Chapa webhook would call; that integration replaces *this view*, not
    the underlying logic.
    """

    def get(self, request, pk):
        with unscoped():
            organization = get_object_or_404(Organization, pk=pk)
        form = RecordPaymentForm(initial={"plan": organization.plan})
        return render(request, "organizations/payment_form.html",
                      {"organization": organization, "form": form})

    def post(self, request, pk):
        with unscoped():
            organization = get_object_or_404(Organization, pk=pk)
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            record_payment(
                organization=organization,
                amount=form.cleaned_data["amount"],
                plan=form.cleaned_data["plan"],
                period_end=form.cleaned_data["period_end"],
                notes=form.cleaned_data.get("notes", ""),
                recorded_by=request.user,
                provider=PaymentProvider.MANUAL,
            )
            messages.success(request, _(
                "Payment recorded. %(name)s's subscription now runs to %(date)s."
            ) % {"name": organization.display_name, "date": form.cleaned_data["period_end"]})
            return redirect("organizations:detail", pk=organization.pk)
        return render(request, "organizations/payment_form.html",
                      {"organization": organization, "form": form})
