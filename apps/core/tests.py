"""
Tests for the Ethiopian calendar and fiscal year configuration.

The calendar tests use anchor dates that can be checked independently:
Ethiopian New Year falls on 11 September, or 12 September in the year before
a Gregorian leap year. If the conversion drifts, those assertions fail long
before anyone notices a wrong fiscal period.
"""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.ethiopian_calendar import (
    days_in_ethiopian_month, ethiopian_new_year, format_ethiopian,
    is_ethiopian_leap_year, to_ethiopian, to_gregorian,
)
from apps.core.fiscal import CalendarSystem, FiscalYear, FiscalYearSettings
from apps.core.services import (
    close_fiscal_year, fiscal_year_for, generate_fiscal_years,
    is_date_postable, reopen_fiscal_year,
)


class EthiopianCalendarTests(TestCase):
    def test_new_year_falls_on_11_or_12_september(self):
        for gregorian_year in range(2015, 2041):
            with self.subTest(year=gregorian_year):
                new_year = ethiopian_new_year(gregorian_year)
                following = gregorian_year + 1
                following_is_leap = (
                    following % 4 == 0 and (following % 100 != 0 or following % 400 == 0)
                )
                self.assertEqual(new_year.month, 9)
                self.assertEqual(new_year.day, 12 if following_is_leap else 11)

    def test_round_trip_over_several_years(self):
        """Every day for ~11 years must survive Gregorian → Ethiopian → Gregorian."""
        day = date(2020, 1, 1)
        for _ in range(4000):
            year, month, dom = to_ethiopian(day)
            self.assertEqual(to_gregorian(year, month, dom), day)
            day += timedelta(days=1)

    def test_leap_years_and_pagume_length(self):
        self.assertTrue(is_ethiopian_leap_year(2015))
        self.assertFalse(is_ethiopian_leap_year(2016))
        self.assertEqual(days_in_ethiopian_month(2015, 13), 6)
        self.assertEqual(days_in_ethiopian_month(2016, 13), 5)
        self.assertEqual(days_in_ethiopian_month(2016, 1), 30)

    def test_hamle_1_is_early_july(self):
        """The fiscal year start must land on 7 or 8 July, never drift far."""
        for ethiopian_year in range(2014, 2031):
            with self.subTest(year=ethiopian_year):
                start = to_gregorian(ethiopian_year, 11, 1)
                self.assertEqual(start.month, 7)
                self.assertIn(start.day, (7, 8))

    def test_invalid_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            to_gregorian(2016, 13, 6)   # Pagume has 5 days in a common year
        with self.assertRaises(ValueError):
            to_gregorian(2016, 14, 1)   # no 14th month
        with self.assertRaises(ValueError):
            to_gregorian(2016, 1, 31)   # months have 30 days

    def test_formatting_in_both_languages(self):
        day = to_gregorian(2017, 11, 1)
        self.assertEqual(format_ethiopian(day, "en"), "1 Hamle 2017")
        self.assertEqual(format_ethiopian(day, "am"), "1 ሐምሌ 2017")


class FiscalYearSettingsTests(TestCase):
    def test_default_is_ethiopian_hamle_1(self):
        settings = FiscalYearSettings.load()
        self.assertEqual(settings.calendar_system, CalendarSystem.ETHIOPIAN)
        self.assertEqual(settings.start_month, 11)   # Hamle
        self.assertEqual(settings.start_day, 1)

    def test_period_for_date_inside_ethiopian_year(self):
        settings = FiscalYearSettings.load()
        start, end, label = settings.period_for(date(2025, 9, 1))
        self.assertEqual(start, date(2025, 7, 8))    # Hamle 1, 2017 EC
        self.assertEqual(end, date(2026, 7, 7))
        self.assertEqual(label, "2017 EC")

    def test_date_before_start_belongs_to_previous_year(self):
        settings = FiscalYearSettings.load()
        _s1, _e1, label_before = settings.period_for(date(2025, 7, 7))
        _s2, _e2, label_after = settings.period_for(date(2025, 7, 8))
        self.assertEqual(label_before, "2016 EC")
        self.assertEqual(label_after, "2017 EC")

    def test_periods_are_contiguous_with_no_gap_or_overlap(self):
        settings = FiscalYearSettings.load()
        probe = date(2024, 1, 1)
        previous_end = None
        for _ in range(8):
            start, end, _label = settings.period_for(probe)
            if previous_end is not None:
                self.assertEqual(start, previous_end + timedelta(days=1))
            self.assertGreater(end, start)
            previous_end = end
            probe = end + timedelta(days=1)

    def test_switching_to_gregorian_january(self):
        settings = FiscalYearSettings.load()
        settings.calendar_system = CalendarSystem.GREGORIAN
        settings.start_month = 1
        settings.start_day = 1
        settings.save()
        start, end, label = settings.period_for(date(2025, 6, 15))
        self.assertEqual(start, date(2025, 1, 1))
        self.assertEqual(end, date(2025, 12, 31))
        self.assertEqual(label, "2025")

    def test_switching_to_gregorian_july(self):
        settings = FiscalYearSettings.load()
        settings.calendar_system = CalendarSystem.GREGORIAN
        settings.start_month = 7
        settings.start_day = 1
        settings.save()
        start, end, label = settings.period_for(date(2025, 8, 1))
        self.assertEqual(start, date(2025, 7, 1))
        self.assertEqual(end, date(2026, 6, 30))
        self.assertEqual(label, "2025/26")

    def test_gregorian_start_day_beyond_28_is_rejected(self):
        settings = FiscalYearSettings.load()
        settings.calendar_system = CalendarSystem.GREGORIAN
        settings.start_month = 2
        settings.start_day = 30
        with self.assertRaises(ValidationError):
            settings.full_clean()

    def test_pagume_start_is_validated(self):
        settings = FiscalYearSettings.load()
        settings.start_month = 13
        settings.start_day = 6
        with self.assertRaises(ValidationError):
            settings.full_clean()

    def test_settings_are_a_singleton(self):
        first = FiscalYearSettings.load()
        second = FiscalYearSettings.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(FiscalYearSettings.objects.count(), 1)


class FiscalYearGenerationTests(TestCase):
    def test_generates_contiguous_years(self):
        years = generate_fiscal_years(from_date=date(2025, 8, 1), count=3)
        self.assertEqual(len(years), 3)
        for earlier, later in zip(years, years[1:]):
            self.assertEqual(later.start_date, earlier.end_date + timedelta(days=1))

    def test_generation_is_idempotent(self):
        generate_fiscal_years(from_date=date(2025, 8, 1), count=3)
        generate_fiscal_years(from_date=date(2025, 8, 1), count=3)
        self.assertEqual(FiscalYear.objects.count(), 3)

    def test_changing_the_rule_does_not_move_existing_years(self):
        """The key guarantee: history keeps its dates when the setting changes."""
        generate_fiscal_years(from_date=date(2025, 8, 1), count=1)
        existing = FiscalYear.objects.get()
        original_start, original_end = existing.start_date, existing.end_date

        settings = FiscalYearSettings.load()
        settings.calendar_system = CalendarSystem.GREGORIAN
        settings.start_month = 1
        settings.start_day = 1
        settings.save()

        existing.refresh_from_db()
        self.assertEqual(existing.start_date, original_start)
        self.assertEqual(existing.end_date, original_end)

    def test_lookup_prefers_a_stored_period_over_the_current_rule(self):
        generate_fiscal_years(from_date=date(2025, 8, 1), count=1)
        stored = FiscalYear.objects.get()

        settings = FiscalYearSettings.load()
        settings.calendar_system = CalendarSystem.GREGORIAN
        settings.start_month = 1
        settings.start_day = 1
        settings.save()

        found = fiscal_year_for(date(2025, 8, 1))
        self.assertEqual(found, stored)


class FiscalYearClosingTests(TestCase):
    def setUp(self):
        self.past = FiscalYear.objects.create(
            label="2015 EC", start_date=date(2023, 7, 8), end_date=date(2024, 7, 7)
        )
        self.middle = FiscalYear.objects.create(
            label="2016 EC", start_date=date(2024, 7, 8), end_date=date(2025, 7, 7)
        )
        self.future = FiscalYear.objects.create(
            label="2099 EC", start_date=date(2098, 7, 8), end_date=date(2099, 7, 7)
        )

    def test_closing_marks_the_year_closed(self):
        close_fiscal_year(fiscal_year=self.past)
        self.past.refresh_from_db()
        self.assertTrue(self.past.is_closed)
        self.assertIsNotNone(self.past.closed_at)

    def test_cannot_close_a_year_that_has_not_ended(self):
        with self.assertRaises(ValidationError):
            close_fiscal_year(fiscal_year=self.future)

    def test_cannot_close_out_of_order(self):
        with self.assertRaises(ValidationError):
            close_fiscal_year(fiscal_year=self.middle)

    def test_cannot_close_twice(self):
        close_fiscal_year(fiscal_year=self.past)
        with self.assertRaises(ValidationError):
            close_fiscal_year(fiscal_year=self.past)

    def test_closed_year_dates_cannot_be_edited(self):
        close_fiscal_year(fiscal_year=self.past)
        self.past.end_date = date(2024, 8, 1)
        with self.assertRaises(ValidationError):
            self.past.save()

    def test_reopening_requires_later_years_to_be_open(self):
        close_fiscal_year(fiscal_year=self.past)
        close_fiscal_year(fiscal_year=self.middle)
        with self.assertRaises(ValidationError):
            reopen_fiscal_year(fiscal_year=self.past, reason="audit adjustment")
        reopen_fiscal_year(fiscal_year=self.middle, reason="audit adjustment")
        reopen_fiscal_year(fiscal_year=self.past, reason="audit adjustment")
        self.past.refresh_from_db()
        self.assertFalse(self.past.is_closed)

    def test_posting_is_blocked_inside_a_closed_year(self):
        close_fiscal_year(fiscal_year=self.past)
        allowed, reason = is_date_postable(date(2023, 12, 1))
        self.assertFalse(allowed)
        self.assertTrue(reason)

        allowed, _reason = is_date_postable(date(2024, 12, 1))
        self.assertTrue(allowed)
