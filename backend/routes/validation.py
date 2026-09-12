"""Form validation helpers.

Each function normalizes one kind of user input and raises ValueError
with a human-friendly message; dispatch() turns that into a 400 page.
"""
import datetime


def require(form, *fields):
    """Raise ValueError when any named field is missing/blank."""
    missing = [f for f in fields if not str(form.get(f, "")).strip()]
    if missing:
        raise ValueError(f"Please fill in: {', '.join(missing)}")


def parse_date(value, label="date"):
    """Validate a YYYY-MM-DD string; returns None for blank, date otherwise."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{label} must be in YYYY-MM-DD format (got '{value}').")


def parse_decimal(value, label="number", minimum=None, maximum=None, allow_blank=False):
    """Validate a decimal number with optional bounds."""
    value = (value or "").strip()
    if not value:
        if allow_blank:
            return None
        raise ValueError(f"{label} is required.")
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{label} must be a number (got '{value}').")
    if minimum is not None and number < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{label} must be at most {maximum}.")
    return number


def parse_int(value, label="value", minimum=None, maximum=None):
    """Validate an integer with optional bounds."""
    value = (value or "").strip()
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{label} must be a whole number (got '{value}').")
    if minimum is not None and number < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{label} must be at most {maximum}.")
    return number


def parse_time(value, label="time"):
    """Validate a HH:MM(:SS) time string and return it normalized to HH:MM:SS."""
    value = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    raise ValueError(f"{label} must be in HH:MM format (got '{value}').")
