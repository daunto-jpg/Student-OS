"""Shared date helpers (Partition A, Member A3)."""
import re
from datetime import date, datetime

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_date(value, label="Date"):
    """Accept 'YYYY-MM-DD' strings, date or datetime. Returns a date.

    Strict on purpose: Python 3.11+ fromisoformat also accepts '20261005',
    which would let inconsistent formats into the database.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if _DATE_RE.fullmatch(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
    raise ValueError(f"{label} must be a real date in YYYY-MM-DD format.")


def today_or(value=None):
    """`value` as a date, or the real today when None (lets tests pass a fake 'today')."""
    return parse_date(value) if value is not None else date.today()
