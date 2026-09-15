"""
Fiscal year configuration and periods.

Why this is a model and not a settings constant
-----------------------------------------------
The accounting engine needs to know which fiscal year a transaction falls in,
and that answer must be **stable for transactions already recorded**. If the
year boundary were a live setting, changing it would silently re-slice every
historical period and every comparative statement with it.

So there are two things here:

* `FiscalYearSettings` — the rule for generating *future* years. Changeable.
* `FiscalYear` — a concrete, dated period. Once created it keeps its dates,
  and once **closed** it cannot be altered at all.

Changing the setting therefore affects years you have not generated yet, and
never rewrites history. That is the behaviour an auditor expects.

Default: the Ethiopian fiscal year, Hamle 1 to Sene 30 — the Ethiopian
government year, which most Ethiopian businesses follow. It is configurable
because a company may file on a different accounting period; confirm the
correct one with your accountant rather than assuming this default.
"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .ethiopian_calendar import (
    MONTH_NAMES_EN, days_in_ethiopian_month, to_ethiopian, to_gregorian,
)


class CalendarSystem(models.TextChoices):
    ETHIOPIAN = "ETHIOPIAN", _("Ethiopian calendar")
    GREGORIAN = "GREGORIAN", _("Gregorian calendar")


class FiscalYearStatus(models.TextChoices):
    OPEN = "OPEN", _("Open")
    CLOSED = "CLOSED", _("Closed")


class FiscalYearSettings(models.Model):
    """The rule used to generate fiscal years. One row."""

    SINGLETON_PK = 1

    calendar_system = models.CharField(
        max_length=12, choices=CalendarSystem.choices, default=CalendarSystem.ETHIOPIAN,
        verbose_name=_("Calendar the year is defined in"),
        help_text=_("Ethiopian means the year starts on a fixed Ethiopian date "
                    "(Hamle 1 by default), so its Gregorian start shifts by a day "
                    "around leap years. Gregorian means a fixed Gregorian date."),
    )
    start_month = models.PositiveSmallIntegerField(
        default=11, validators=[MinValueValidator(1), MaxValueValidator(13)],
        verbose_name=_("Start Month"),
        help_text=_("In the chosen calendar. Ethiopian month 11 is Hamle — the "
                    "start of the Ethiopian government fiscal year."),
    )
    start_day = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name=_("Start Day"),
    )
    display_calendar = models.CharField(
        max_length=12, choices=CalendarSystem.choices, default=CalendarSystem.GREGORIAN,
        verbose_name=_("Calendar shown to users"),
        help_text=_("Which calendar dates are displayed in. Independent of the "
                    "fiscal year rule — you can run an Ethiopian fiscal year while "
                    "showing Gregorian dates on screen."),
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fiscal_settings_updates", verbose_name=_("Updated By"),
    )

    class Meta:
        verbose_name = _("Fiscal Year Settings")
        verbose_name_plural = _("Fiscal Year Settings")

    def __str__(self):
        return f"{self.get_calendar_system_display()} — starts {self.start_label}"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj

    def clean(self):
        super().clean()
        if self.calendar_system == CalendarSystem.GREGORIAN:
            if self.start_month > 12:
                raise ValidationError({
                    "start_month": _("The Gregorian calendar has 12 months.")
                })
            if self.start_day > 28:
                # Beyond the 28th a start date cannot exist in every month
                # (February), which would make some years ungenerable.
                raise ValidationError({
                    "start_day": _("Use a day between 1 and 28 so the start date "
                                   "exists in every month.")
                })
        else:
            if self.start_month == 13 and self.start_day > 5:
                raise ValidationError({
                    "start_day": _("Pagume has only 5 days in a common year, so a "
                                   "fiscal year cannot start after Pagume 5.")
                })
            if self.start_day > 30:
                raise ValidationError({
                    "start_day": _("Ethiopian months have at most 30 days.")
                })

    @property
    def start_label(self):
        if self.calendar_system == CalendarSystem.ETHIOPIAN:
            return f"{self.start_day} {MONTH_NAMES_EN[self.start_month - 1]}"
        import calendar

        return f"{self.start_day} {calendar.month_name[self.start_month]}"

    # -- generating periods ------------------------------------------------
    def period_for(self, on_date):
        """(start, end, label) of the fiscal year containing `on_date`.

        Computed from the rule, without touching the database, so it can be
        used to decide which `FiscalYear` a transaction belongs to before one
        has been generated.
        """
        if self.calendar_system == CalendarSystem.ETHIOPIAN:
            return self._ethiopian_period(on_date)
        return self._gregorian_period(on_date)

    def _ethiopian_period(self, on_date):
        eth_year, eth_month, eth_day = to_ethiopian(on_date)
        # If we are before the start date within this Ethiopian year, the
        # fiscal year began in the previous Ethiopian year.
        if (eth_month, eth_day) < (self.start_month, self.start_day):
            fy_year = eth_year - 1
        else:
            fy_year = eth_year
        start = to_gregorian(fy_year, self.start_month, self._safe_eth_day(fy_year))
        next_start = to_gregorian(
            fy_year + 1, self.start_month, self._safe_eth_day(fy_year + 1)
        )
        end = next_start - timezone.timedelta(days=1)
        # Labelled by the Ethiopian year it starts in, e.g. "2017 EC".
        return start, end, f"{fy_year} EC"

    def _safe_eth_day(self, eth_year):
        """Clamps the start day to a day that exists in that month.

        Only bites for Pagume, which has 5 days in a common year and 6 in a
        leap year — a fiscal year starting Pagume 6 would otherwise fail to
        generate four years out of five.
        """
        return min(self.start_day, days_in_ethiopian_month(eth_year, self.start_month))

    def _gregorian_period(self, on_date):
        import datetime

        if (on_date.month, on_date.day) < (self.start_month, self.start_day):
            fy_year = on_date.year - 1
        else:
            fy_year = on_date.year
        start = datetime.date(fy_year, self.start_month, self.start_day)
        next_start = datetime.date(fy_year + 1, self.start_month, self.start_day)
        end = next_start - datetime.timedelta(days=1)
        label = str(fy_year) if (self.start_month, self.start_day) == (1, 1) \
            else f"{fy_year}/{str(fy_year + 1)[-2:]}"
        return start, end, label


class FiscalYear(models.Model):
    """A concrete accounting period.

    Dates are stored, not recomputed, so changing the settings later cannot
    move a period that transactions have already been posted into.
    """

    label = models.CharField(
        max_length=32, unique=True, verbose_name=_("Label"),
        help_text=_("e.g. '2017 EC' or '2025/26'."),
    )
    start_date = models.DateField(db_index=True, verbose_name=_("Start Date"))
    end_date = models.DateField(db_index=True, verbose_name=_("End Date"))
    status = models.CharField(
        max_length=8, choices=FiscalYearStatus.choices, default=FiscalYearStatus.OPEN,
        db_index=True, verbose_name=_("Status"),
    )
    calendar_system = models.CharField(
        max_length=12, choices=CalendarSystem.choices, default=CalendarSystem.ETHIOPIAN,
        verbose_name=_("Defined In"),
        help_text=_("The rule in force when this year was generated, kept for the "
                    "record even if the setting later changes."),
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed At"))
    closed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fiscal_years_closed", verbose_name=_("Closed By"),
    )
    note = models.CharField(max_length=255, blank=True, verbose_name=_("Note"))

    class Meta:
        verbose_name = _("Fiscal Year")
        verbose_name_plural = _("Fiscal Years")
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="fiscal_year_ends_after_it_starts",
            )
        ]

    def __str__(self):
        return self.label

    @property
    def is_closed(self):
        return self.status == FiscalYearStatus.CLOSED

    @property
    def is_current(self):
        return self.start_date <= timezone.localdate() <= self.end_date

    def contains(self, on_date):
        return self.start_date <= on_date <= self.end_date

    @property
    def ethiopian_range(self):
        """Both ends in Ethiopian terms, for display."""
        from .ethiopian_calendar import format_ethiopian

        return (format_ethiopian(self.start_date), format_ethiopian(self.end_date))

    def save(self, *args, **kwargs):
        if self.pk and self.is_closed:
            existing = FiscalYear.objects.filter(pk=self.pk).first()
            # A closed period is a fixed fact. Reopening is a deliberate,
            # separate action (`reopen`), not a side effect of saving.
            if existing and existing.is_closed and not kwargs.pop("_force", False):
                changed = (existing.start_date != self.start_date
                           or existing.end_date != self.end_date)
                if changed:
                    raise ValidationError(
                        _("A closed fiscal year's dates cannot be changed.")
                    )
        super().save(*args, **kwargs)
