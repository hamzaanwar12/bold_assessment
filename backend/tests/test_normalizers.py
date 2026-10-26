"""Unit tests for the pure normalizers that sit on the rejection boundary.

Note: the ticket (04-normalization-and-validation.md) explicitly says these
functions are not a seam and asks for no unit-test file, reasoning that every
outcome is already observable through the Import Report. The task author
overrode that instruction for this ticket only, because the HTTP endpoint
that would exercise them does not exist yet (it is built in a later ticket).
These tests exist to drive the TDD loop now; whether they survive once the
HTTP seam (ticket 09) covers the same ground is a decision for integration.
"""

from decimal import Decimal

import pytest

from app.normalizers import (
    NormalizationError,
    normalize_applied_date,
    normalize_email,
    normalize_region,
    normalize_salary,
    normalize_status,
    normalize_text,
)


class TestNormalizeEmail:
    def test_trims_and_lowercases(self):
        assert normalize_email("  Alicia.Trent@Gmail.com ") == "alicia.trent@gmail.com"

    def test_rejects_missing_at_sign_with_at_bracket(self):
        with pytest.raises(NormalizationError):
            normalize_email("marcus.reed[at]gmail.com")

    def test_rejects_missing_at_sign_entirely(self):
        with pytest.raises(NormalizationError):
            normalize_email("tina.holloway.gmail.com")

    def test_rejects_empty(self):
        with pytest.raises(NormalizationError):
            normalize_email("")

    def test_rejects_none(self):
        with pytest.raises(NormalizationError):
            normalize_email(None)

    def test_rejection_reason_names_field_and_value(self):
        with pytest.raises(NormalizationError) as excinfo:
            normalize_email("tina.holloway.gmail.com")
        err = excinfo.value
        assert err.field == "email"
        assert "tina.holloway.gmail.com" in err.reason


class TestNormalizeRegion:
    def test_lowercase_is_uppercased(self):
        assert normalize_region("us-mw") == "US-MW"

    def test_trims_surrounding_whitespace(self):
        assert normalize_region(" CO-BOG ") == "CO-BOG"

    def test_rejects_missing_hyphen_not_repaired(self):
        # USW must NOT be repaired to US-W: a one-character inference on the
        # authorization axis is out of bounds.
        with pytest.raises(NormalizationError):
            normalize_region("USW")

    def test_rejects_code_not_in_reference_list(self):
        with pytest.raises(NormalizationError):
            normalize_region("ZZ-99")

    def test_rejects_empty_even_though_region_is_otherwise_valid(self):
        # An empty Region is rejected, never a null Region: a Candidate with
        # no Region is invisible to every scoped Recruiter.
        with pytest.raises(NormalizationError):
            normalize_region("")

    def test_rejects_none(self):
        with pytest.raises(NormalizationError):
            normalize_region(None)

    def test_accepts_all_six_canonical_codes(self):
        for code in ("US-MW", "US-NE", "US-SE", "US-W", "PH-MNL", "CO-BOG"):
            assert normalize_region(code) == code


class TestNormalizeStatus:
    def test_case_fold(self):
        assert normalize_status("ACTIVE") == "active"

    def test_rejects_misspelling_no_fuzzy_match(self):
        with pytest.raises(NormalizationError):
            normalize_status("actve")

    def test_rejects_unrecognised_status_no_catchall(self):
        with pytest.raises(NormalizationError):
            normalize_status("on hold")

    def test_rejects_empty(self):
        with pytest.raises(NormalizationError):
            normalize_status("")

    def test_accepts_all_four_canonical_statuses(self):
        for value in ("active", "screening", "interviewing", "withdrawn"):
            assert normalize_status(value.upper()) == value


class TestNormalizeAppliedDate:
    def test_parses_us_slash_format(self):
        import datetime

        assert normalize_applied_date("06/30/2026") == datetime.date(2026, 6, 30)

    def test_parses_text_month_format(self):
        import datetime

        assert normalize_applied_date("14-May-2026") == datetime.date(2026, 5, 14)

    def test_parses_iso_format(self):
        import datetime

        assert normalize_applied_date("2026-05-14") == datetime.date(2026, 5, 14)

    def test_rejects_impossible_calendar_date(self):
        with pytest.raises(NormalizationError):
            normalize_applied_date("2026-02-30")

    def test_empty_loads_as_unknown_not_rejected(self):
        # Deliberate asymmetry: a blank cell asserts nothing.
        assert normalize_applied_date("") is None

    def test_none_loads_as_unknown(self):
        assert normalize_applied_date(None) is None


class TestNormalizeSalary:
    def test_strips_dollar_sign_and_commas(self):
        assert normalize_salary("$95,000") == Decimal("95000")

    def test_strips_commas_only(self):
        assert normalize_salary("97,500") == Decimal("97500")

    def test_expands_k_suffix(self):
        assert normalize_salary("85k") == Decimal("85000")

    def test_expands_uppercase_k_suffix(self):
        assert normalize_salary("85K") == Decimal("85000")

    def test_non_numeric_loads_as_unknown_not_rejected(self):
        assert normalize_salary("negotiable") is None

    def test_empty_loads_as_unknown(self):
        assert normalize_salary("") is None

    def test_none_loads_as_unknown(self):
        assert normalize_salary(None) is None

    def test_plain_integer_string(self):
        assert normalize_salary("88000") == Decimal("88000")


class TestNormalizeText:
    def test_trims_whitespace(self):
        assert normalize_text("  Indeed  ") == "Indeed"

    def test_empty_becomes_none(self):
        assert normalize_text("") is None

    def test_none_stays_none(self):
        assert normalize_text(None) is None

    def test_preserves_unicode_byte_exact(self):
        for name in ("Nguyễn Thị Hoa", "Jürgen Müller", "Wesley Trần", "Sofía", "Tomás", "Lucía"):
            assert normalize_text(name) == name

    def test_stores_sql_injection_payload_as_literal_text(self):
        payload = "O'Connor'); DROP TABLE candidates;--"
        assert normalize_text(payload) == payload
