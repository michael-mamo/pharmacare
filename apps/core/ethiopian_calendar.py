"""
Ethiopian calendar conversion.

The Ethiopian calendar has 13 months: twelve of exactly 30 days, then Pagume
with 5 days (6 in a leap year). A leap year is one where `year % 4 == 3`,
which is why the Gregorian date of Ethiopian New Year alternates between
11 and 12 September.

Conversion goes through the Julian Day Number rather than by counting
offsets, because JDN is calendar-agnostic and the round trip is provably
exact. The epoch constant below is the JDN of Meskerem 1, year 1 in the
Amete Mihret era — the era in ordinary civil use in Ethiopia.

Everything here is pure arithmetic with no external dependency, and it is
covered by tests against known anchor dates (Ethiopian New Year, and the
Hamle 1 fiscal year start) so a subtle off-by-one cannot pass unnoticed.
"""
from datetime import date

#: JDN of Meskerem 1, year 1, Amete Mihret.
JD_EPOCH_OFFSET_AMETE_MIHRET = 1723856

MONTH_NAMES_EN = [
    "Meskerem", "Tikimt", "Hidar", "Tahsas", "Tir", "Yekatit",
    "Megabit", "Miyazia", "Ginbot", "Sene", "Hamle", "Nehase", "Pagume",
]
MONTH_NAMES_AM = [
    "መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት",
    "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ",
]


def is_ethiopian_leap_year(year):
    """Ethiopian leap years are those where year % 4 == 3 — the year before
    a Gregorian leap year, which is why New Year shifts to 12 September."""
    return year % 4 == 3


def days_in_ethiopian_month(year, month):
    if month < 1 or month > 13:
        raise ValueError("Ethiopian month must be between 1 and 13.")
    if month == 13:
        return 6 if is_ethiopian_leap_year(year) else 5
    return 30


def _gregorian_to_jdn(year, month, day):
    """Standard Fliegel–Van Flandern algorithm, valid for all Gregorian dates."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100
            + y // 400 - 32045)


def _jdn_to_gregorian(jdn):
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def _ethiopian_to_jdn(year, month, day):
    return (JD_EPOCH_OFFSET_AMETE_MIHRET + 365) + 365 * (year - 1) \
        + year // 4 + 30 * month + day - 31


def _jdn_to_ethiopian(jdn):
    r = (jdn - JD_EPOCH_OFFSET_AMETE_MIHRET) % 1461
    n = (r % 365) + 365 * (r // 1460)
    year = (4 * ((jdn - JD_EPOCH_OFFSET_AMETE_MIHRET) // 1461)
            + (r // 365) - (r // 1460))
    month = (n // 30) + 1
    day = (n % 30) + 1
    return year, month, day


def to_ethiopian(gregorian_date):
    """Gregorian `date` → (year, month, day) in the Ethiopian calendar."""
    jdn = _gregorian_to_jdn(
        gregorian_date.year, gregorian_date.month, gregorian_date.day
    )
    return _jdn_to_ethiopian(jdn)


def to_gregorian(year, month, day):
    """Ethiopian (year, month, day) → Gregorian `date`."""
    if not 1 <= month <= 13:
        raise ValueError("Ethiopian month must be between 1 and 13.")
    if day < 1 or day > days_in_ethiopian_month(year, month):
        raise ValueError(
            f"Day {day} is out of range for Ethiopian month {month} of {year}."
        )
    g_year, g_month, g_day = _jdn_to_gregorian(_ethiopian_to_jdn(year, month, day))
    return date(g_year, g_month, g_day)


def format_ethiopian(gregorian_date, language="en", with_year=True):
    """Human-readable Ethiopian date, e.g. '1 Hamle 2017' / '1 ሐምሌ 2017'."""
    year, month, day = to_ethiopian(gregorian_date)
    names = MONTH_NAMES_AM if language.startswith("am") else MONTH_NAMES_EN
    name = names[month - 1]
    return f"{day} {name} {year}" if with_year else f"{day} {name}"


def ethiopian_new_year(gregorian_year):
    """Gregorian date of Meskerem 1 falling in the given Gregorian year.

    Useful as a sanity anchor: it is 11 September, or 12 September when the
    following Gregorian year is a leap year.
    """
    # Find the Ethiopian year whose Meskerem 1 lands in this Gregorian year.
    probe = date(gregorian_year, 9, 15)
    eth_year, _m, _d = to_ethiopian(probe)
    return to_gregorian(eth_year, 1, 1)
