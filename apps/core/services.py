"""Fiscal year services."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .fiscal import FiscalYear, FiscalYearSettings, FiscalYearStatus


def fiscal_year_for(on_date=None, create=False):
    """The FiscalYear containing `on_date`, optionally generating it.

    Looks for a stored period first, so a year whose dates were generated
    under an older rule keeps those dates. Only falls back to the current
    rule when no stored period covers the date.
    """
    on_date = on_date or timezone.localdate()
    existing = FiscalYear.objects.filter(
        start_date__lte=on_date, end_date__gte=on_date
    ).first()
    if existing or not create:
        return existing

    settings = FiscalYearSettings.load()
    start, end, label = settings.period_for(on_date)
    year, _created = FiscalYear.objects.get_or_create(
        start_date=start,
        defaults={"end_date": end, "label": label,
                  "calendar_system": settings.calendar_system},
    )
    return year


@transaction.atomic
def generate_fiscal_years(from_date=None, count=3):
    """Creates the next `count` fiscal years from the current rule.

    Existing periods are never modified — only gaps are filled. That is what
    allows the start date to be changed without disturbing years already in
    use.
    """
    settings = FiscalYearSettings.load()
    on_date = from_date or timezone.localdate()
    created = []
    for _ in range(count):
        start, end, label = settings.period_for(on_date)
        if not FiscalYear.objects.filter(start_date=start).exists():
            # Guard against a label clash when the rule changes mid-stream and
            # two different periods would otherwise want the same name.
            unique_label = label
            suffix = 2
            while FiscalYear.objects.filter(label=unique_label).exists():
                unique_label = f"{label} ({suffix})"
                suffix += 1
            created.append(FiscalYear.objects.create(
                start_date=start, end_date=end, label=unique_label,
                calendar_system=settings.calendar_system,
            ))
        on_date = end + timezone.timedelta(days=1)
    return created


@transaction.atomic
def close_fiscal_year(*, fiscal_year, user=None, note=""):
    """Closes a period. Nothing may be posted into it afterwards."""
    if fiscal_year.is_closed:
        raise ValidationError(_("This fiscal year is already closed."))
    if fiscal_year.end_date >= timezone.localdate():
        raise ValidationError(
            _("%(label)s has not ended yet (it runs to %(end)s), so it cannot "
              "be closed.") % {"label": fiscal_year.label, "end": fiscal_year.end_date}
        )
    earlier_open = FiscalYear.objects.filter(
        end_date__lt=fiscal_year.start_date, status=FiscalYearStatus.OPEN
    ).order_by("start_date").first()
    if earlier_open:
        # Closing out of order would leave an unclosed gap behind a closed
        # period, which makes opening balances meaningless.
        raise ValidationError(
            _("Close %(earlier)s first — fiscal years must be closed in order.")
            % {"earlier": earlier_open.label}
        )

    fiscal_year.status = FiscalYearStatus.CLOSED
    fiscal_year.closed_at = timezone.now()
    fiscal_year.closed_by = user
    if note:
        fiscal_year.note = note
    fiscal_year.save(update_fields=["status", "closed_at", "closed_by", "note"])
    return fiscal_year


@transaction.atomic
def reopen_fiscal_year(*, fiscal_year, user=None, reason=""):
    """Reopens a closed period. Deliberately a separate, explicit action."""
    if not fiscal_year.is_closed:
        raise ValidationError(_("This fiscal year is not closed."))
    later_closed = FiscalYear.objects.filter(
        start_date__gt=fiscal_year.start_date, status=FiscalYearStatus.CLOSED
    ).order_by("start_date").first()
    if later_closed:
        raise ValidationError(
            _("Reopen %(later)s first — later years are already closed.")
            % {"later": later_closed.label}
        )
    fiscal_year.status = FiscalYearStatus.OPEN
    fiscal_year.closed_at = None
    fiscal_year.closed_by = None
    fiscal_year.note = (fiscal_year.note + f" | Reopened: {reason}").strip(" |")[:255]
    fiscal_year.save(update_fields=["status", "closed_at", "closed_by", "note"])
    return fiscal_year


def is_date_postable(on_date):
    """Whether a transaction may be recorded on this date.

    Returns (allowed, reason). The accounting engine will call this before
    posting; today it is used to warn on back-dated stock and sales entries.
    """
    year = fiscal_year_for(on_date)
    if year is None:
        return True, ""
    if year.is_closed:
        return False, _("%(label)s is closed, so nothing can be recorded on "
                        "%(date)s.") % {"label": year.label, "date": on_date}
    return True, ""
