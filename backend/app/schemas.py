"""The explicit definition of a valid Candidate, plus the Import Report shape.

Constructing `Candidate` IS validation: a Source Row that cannot populate
every field here (via the normalizers in `app.normalizers`) is a Rejection,
not a Candidate. See spec.md ("Normalization and the rejection boundary")
and GLOSSARY.md for the vocabulary used below.

Scope note: this module defines the Candidate shape and the Import Report
shape only. It does not know about the database, the import endpoint, or
deduplication — those are owned by other tickets.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.normalizers import (
    normalize_applied_date,
    normalize_email,
    normalize_region,
    normalize_salary,
    normalize_status,
    normalize_text,
)

# Free-text fields that are trimmed and stored verbatim, never interpreted.
_TEXT_FIELDS = ("legacy_candidate_id", "first_name", "last_name", "phone", "desired_role", "source", "notes")


class Candidate(BaseModel):
    """A valid Candidate: the result of successfully normalizing a Source Row.

    A Candidate belongs to exactly one Region and is identified by its
    Normalized Email (GLOSSARY.md: Candidate, Normalized Email). Raising
    during construction (a `pydantic.ValidationError` wrapping a
    `NormalizationError`) is how a Source Row becomes a Rejection.
    """

    legacy_candidate_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None
    region_code: str
    desired_role: str | None = None
    salary_expectation: Decimal | None = None
    applied_date: date | None = None
    status: str
    source: str | None = None
    notes: str | None = None

    @field_validator(*_TEXT_FIELDS, mode="before")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        return normalize_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str | None) -> str:
        return normalize_email(value)

    @field_validator("region_code", mode="before")
    @classmethod
    def _normalize_region(cls, value: str | None) -> str:
        return normalize_region(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: str | None) -> str:
        return normalize_status(value)

    @field_validator("applied_date", mode="before")
    @classmethod
    def _normalize_applied_date(cls, value: str | None) -> date | None:
        return normalize_applied_date(value)

    @field_validator("salary_expectation", mode="before")
    @classmethod
    def _normalize_salary(cls, value: str | None) -> Decimal | None:
        return normalize_salary(value)


class RejectedRow(BaseModel):
    """One rejected Source Row: its 1-based row number and a human-readable reason."""

    row: int
    reason: str


class ImportReport(BaseModel):
    """The result of an Import (GLOSSARY.md: Import Report).

    `imported` and `merged` count Source Rows by Import Outcome; `rejected`
    carries every Rejection with its row number and reason, so nothing is
    silently dropped.
    """

    imported: int
    merged: int
    rejected: list[RejectedRow]
