"""Pure normalizers for a Source Row's fields.

Each normalizer answers one question for its field: is this value absent, or
is it wrong? Absent values that are not identity-bearing load as unknown
(`None`). Wrong values raise `NormalizationError`, which carries a
human-readable reason naming the field and the offending value, suitable for
the Import Report.

Three rules are deliberate and must not be "improved" into something softer:

- Region is the authorization axis. `USW` is rejected, not repaired to
  `US-W` — a one-character inference here is out of bounds. An empty Region
  is rejected too, even when the rest of the row is fine, because a
  Region-less Candidate is invisible to every scoped Recruiter.
- Candidate Status has no fuzzy matching and no catch-all member. `actve`
  and `on hold` are rejected rather than guessed, because guessing invents
  business meaning.
- Applied date is asymmetric on purpose: an empty cell loads as unknown
  (`None`), but an impossible calendar date (`2026-02-30`) is rejected,
  because coercing it would fabricate a fact.

See spec.md ("Normalization and the rejection boundary") and GLOSSARY.md.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# The six canonical Region codes (GLOSSARY.md: Region).
CANONICAL_REGIONS = frozenset({"US-MW", "US-NE", "US-SE", "US-W", "PH-MNL", "CO-BOG"})

# The canonical Candidate Status enum (GLOSSARY.md: Candidate Status).
CANONICAL_STATUSES = frozenset({"active", "screening", "interviewing", "withdrawn"})

# Deliberately simple: good enough to catch "no @" and "no domain" without
# pretending to be a full RFC 5322 validator.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Accepted applied-date formats, in the order they are tried.
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y")

# Parsed explicitly rather than with %b, which reads the C library's locale
# tables: under LC_TIME=de_DE, "14-May-2026" would not parse. Setup must work
# on a clean machine whatever its locale.
_MONTH_ABBREVIATIONS = {
    m: i
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}
_TEXT_DATE_PATTERN = re.compile(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$")


class NormalizationError(ValueError):
    """Raised when a field's raw value cannot be normalized into a valid Candidate.

    Carries enough structure for a Pydantic validator to re-raise it (so it
    surfaces as a ValidationError) and enough prose for a human reading the
    Import Report.
    """

    def __init__(self, field: str, value: str, reason: str) -> None:
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(reason)


def normalize_email(raw: str | None) -> str:
    """Trim and lowercase an email. Reject malformed or empty values.

    Email is the Candidate identity (ADR 0001) — there is no "unknown"
    email, only a valid one or a Rejection.
    """
    value = (raw or "").strip().lower()
    if not value or not _EMAIL_PATTERN.match(value):
        raise NormalizationError("email", raw or "", f"email {raw!r} is malformed or empty")
    return value


def normalize_region(raw: str | None) -> str:
    """Trim and uppercase a Region code. Reject anything not one of the six canonical codes, including empty."""
    value = (raw or "").strip().upper()
    if not value or value not in CANONICAL_REGIONS:
        raise NormalizationError(
            "region_code", raw or "", f"region {raw!r} is not one of the six canonical Region codes"
        )
    return value


def normalize_status(raw: str | None) -> str:
    """Case-fold a Candidate Status. Reject anything not in the canonical enum."""
    value = (raw or "").strip().lower()
    if value not in CANONICAL_STATUSES:
        raise NormalizationError(
            "status", raw or "", f"status {raw!r} is not a recognised Candidate Status"
        )
    return value


def normalize_applied_date(raw: str | None) -> date | None:
    """Parse an applied date in one of the accepted formats.

    An empty value loads as unknown (`None`). A value that parses to no real
    calendar date is rejected.
    """
    value = (raw or "").strip()
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    if match := _TEXT_DATE_PATTERN.match(value):
        day, month_abbr, year = match.groups()
        if month := _MONTH_ABBREVIATIONS.get(month_abbr.lower()):
            try:
                return date(int(year), month, int(day))
            except ValueError:
                pass  # a real-looking but impossible day, e.g. 30-Feb-2026
    raise NormalizationError(
        "applied_date", raw or "", f"applied date {raw!r} does not parse to a real calendar date"
    )


def normalize_salary(raw: str | None) -> Decimal | None:
    """Strip currency symbols/commas/whitespace and expand a k/K suffix.

    Never rejects: a non-numeric or empty value loads as unknown (`None`).
    """
    value = (raw or "").strip()
    if not value:
        return None
    cleaned = value.replace("$", "").replace(",", "").strip()
    has_k_suffix = cleaned[-1:].lower() == "k"
    if has_k_suffix:
        cleaned = cleaned[:-1]
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    # Decimal() accepts "NaN", "sNaN" and "Infinity" without raising, and
    # PostgreSQL NUMERIC stores 'NaN' happily -- so without this guard a
    # legacy export containing "NaN" would persist a non-numeric salary that
    # later arithmetic blows up on. Not a number means unknown.
    if not amount.is_finite():
        return None
    if has_k_suffix:
        amount *= 1000
    return amount


def normalize_text(raw: str | None) -> str | None:
    """Trim a free-text field. Never rejects; stores the value verbatim otherwise.

    Used for names, phone, desired role, source, and notes — fields that are
    stored as literal text, not interpreted. Preserves Unicode byte-exact.
    """
    if raw is None:
        return None
    value = raw.strip()
    return value or None
