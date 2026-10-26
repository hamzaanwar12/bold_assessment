"""Unit tests for the Candidate schema that defines what a valid Candidate is.

Same note as test_normalizers.py: these are added despite the ticket's "not a
seam" instruction, as an explicit exception for this ticket, because the
endpoint that would otherwise exercise validation does not exist yet.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import Candidate, ImportReport, RejectedRow


def _row(**overrides):
    base = {
        "legacy_candidate_id": "C-1001",
        "first_name": "Alicia",
        "last_name": "Trent",
        "email": "  Alicia.Trent@Gmail.com ",
        "phone": "+1 (734) 555-0142",
        "region_code": "US-MW",
        "desired_role": "Full-Stack Engineer",
        "salary_expectation": "$95,000",
        "applied_date": "2026-05-14",
        "status": "Active",
        "source": "LinkedIn",
        "notes": "Strong React portfolio",
    }
    base.update(overrides)
    return base


class TestCandidateAcceptsAndNormalizesAValidRow:
    def test_builds_from_a_well_formed_row(self):
        candidate = Candidate(**_row())
        assert candidate.email == "alicia.trent@gmail.com"
        assert candidate.region_code == "US-MW"
        assert candidate.status == "active"
        assert candidate.salary_expectation == Decimal("95000")

    def test_accepts_empty_applied_date_as_unknown(self):
        candidate = Candidate(**_row(applied_date=""))
        assert candidate.applied_date is None

    def test_accepts_non_numeric_salary_as_unknown(self):
        candidate = Candidate(**_row(salary_expectation="negotiable"))
        assert candidate.salary_expectation is None

    def test_accepts_missing_phone(self):
        candidate = Candidate(**_row(phone=""))
        assert candidate.phone is None

    def test_preserves_unicode_names_byte_exact(self):
        candidate = Candidate(**_row(first_name="Nguyễn", last_name="Thị Hoa"))
        assert candidate.first_name == "Nguyễn"
        assert candidate.last_name == "Thị Hoa"

    def test_stores_sql_injection_payload_as_literal_text(self):
        payload = "O'Connor'); DROP TABLE candidates;--"
        candidate = Candidate(**_row(last_name=payload))
        assert candidate.last_name == payload


class TestCandidateRejectsInvalidRows:
    def test_rejects_malformed_email(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(email="tina.holloway.gmail.com"))

    def test_rejects_empty_email(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(email=""))

    def test_rejects_unresolvable_region(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(region_code="USW"))

    def test_rejects_empty_region(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(region_code=""))

    def test_rejects_unrecognised_status(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(status="on hold"))

    def test_rejects_impossible_applied_date(self):
        with pytest.raises(ValidationError):
            Candidate(**_row(applied_date="2026-02-30"))


class TestImportReportShape:
    def test_builds_the_report_shape(self):
        report = ImportReport(
            imported=48,
            merged=2,
            rejected=[RejectedRow(row=34, reason="email 'marcus.reed[at]gmail.com' is malformed or empty")],
        )
        assert report.imported == 48
        assert report.merged == 2
        assert report.rejected[0].row == 34
        assert "malformed" in report.rejected[0].reason


class TestSourceColumnMapping:
    """The suite constructed Candidate(...) directly, so it never crossed the
    CSV->model boundary. That gap hid a whole field being dropped: the source
    column is `candidate_id`, the field is `legacy_candidate_id`, and without
    an alias every Candidate silently lost its traceability (ADR 0001)."""

    def test_candidate_id_column_populates_legacy_candidate_id(self) -> None:
        candidate = Candidate.model_validate(
            {
                "candidate_id": "C-1001",
                "first_name": "Alicia",
                "last_name": "Trent",
                "email": "alicia.trent@gmail.com",
                "region_code": "US-MW",
                "status": "Active",
            }
        )
        assert candidate.legacy_candidate_id == "C-1001"

    def test_field_name_still_works_for_direct_construction(self) -> None:
        candidate = Candidate(
            legacy_candidate_id="C-1001",
            email="a@b.com",
            region_code="US-MW",
            status="active",
        )
        assert candidate.legacy_candidate_id == "C-1001"
