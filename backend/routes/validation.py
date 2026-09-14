"""Form validation helpers.

Each function normalizes one kind of user input and raises ValueError
with a human-friendly message; dispatch() turns that into a 400 page.

The pattern (viva answer): forms ALSO carry HTML5 validation attributes
(required, type=number...), so the browser gives instant feedback — but
"never trust the client": the server re-checks everything here, because
curl/anyone can POST straight past the browser. One raise site per
problem, one rendering site (the 400 page), zero scattered if-checks in
handlers.
"""
import datetime


def require(form, *fields):
    """Raise ValueError when any named field is missing/blank."""
    missing = [f for f in fields if not str(form.get(f, "")).strip()]
    if missing:
        raise ValueError(f"Please fill in: {', '.join(missing)}")


def parse_date(value, label="date"):
    """Validate a YYYY-MM-DD string; returns None for blank, date otherwise.

    None-for-blank is the contract that lets optional date fields work:
    handlers decide whether None is acceptable (attendance requires a
    date, a student's contact doesn't).
    """
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{label} must be in YYYY-MM-DD format (got '{value}').")


def parse_decimal(value, label="number", minimum=None, maximum=None):
    """Validate a decimal number with optional bounds.

    minimum/maximum exist for marks (0..max_marks) — bounds are policy,
    and policy lives in one helper rather than in every handler.
    """
    value = (value or "").strip()
    if not value:
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
    # int(), not float(): ids and counts must be whole numbers by type,
    # independent of any bounds.
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
    """Validate a HH:MM(:SS) time string and return it normalized to HH:MM:SS.

    Normalizing ('09:00' -> '09:00:00') is the quiet win: MySQL TIME
    columns get one canonical shape no matter what the form sent.
    """
    value = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    raise ValueError(f"{label} must be in HH:MM format (got '{value}').")
