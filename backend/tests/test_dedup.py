"""Unit tests for deduplication and merge, pure in-memory logic over already-
validated Candidates (app.dedup). No database, no endpoint — see
05-dedup-and-merge.md.
"""

from datetime import date
from decimal import Decimal

from app.dedup import MergeOutcome, deduplicate, merge_candidate
from app.schemas import Candidate


def _candidate(**overrides):
    base = {
        "legacy_candidate_id": "C-1001",
        "first_name": "Alicia",
        "last_name": "Trent",
        "email": "alicia.trent@gmail.com",
        "phone": "+1 (734) 555-0142",
        "region_code": "US-MW",
        "desired_role": "Full-Stack Engineer",
        "salary_expectation": "95000",
        "applied_date": "2026-05-14",
        "status": "active",
        "source": "LinkedIn",
        "notes": "Strong React portfolio",
    }
    base.update(overrides)
    return Candidate(**base)


class TestMergeCandidate:
    def test_no_existing_record_returns_incoming_unchanged(self):
        incoming = _candidate()
        assert merge_candidate(None, incoming) == incoming

    def test_last_writer_wins_for_non_null_fields(self):
        existing = _candidate(source="LinkedIn", notes="Strong React portfolio")
        incoming = _candidate(source="Indeed", notes="Possible re-application")
        merged = merge_candidate(existing, incoming)
        assert merged.source == "Indeed"
        assert merged.notes == "Possible re-application"

    def test_null_in_incoming_never_overwrites_non_null_in_existing(self):
        existing = _candidate(notes="Has detail")
        incoming = _candidate(notes=None)
        merged = merge_candidate(existing, incoming)
        assert merged.notes == "Has detail"

    def test_null_in_existing_is_overwritten_by_non_null_incoming(self):
        existing = _candidate(notes=None)
        incoming = _candidate(notes="New detail")
        merged = merge_candidate(existing, incoming)
        assert merged.notes == "New detail"

    def test_both_null_stays_null(self):
        existing = _candidate(notes=None)
        incoming = _candidate(notes=None)
        merged = merge_candidate(existing, incoming)
        assert merged.notes is None

    def test_exact_duplicate_row_merges_to_itself(self):
        existing = _candidate()
        incoming = _candidate()
        merged = merge_candidate(existing, incoming)
        assert merged == existing


class TestDeduplicate:
    def test_single_row_is_an_import(self):
        outcomes = deduplicate([_candidate()])
        assert len(outcomes) == 1
        assert outcomes[0].is_merge is False
        assert outcomes[0].candidate.email == "alicia.trent@gmail.com"

    def test_exact_duplicate_row_counts_as_merge_not_import(self):
        row = _candidate(legacy_candidate_id="C-1004")
        outcomes = deduplicate([row, row])
        assert len(outcomes) == 1
        assert outcomes[0].is_merge is True
        assert outcomes[0].candidate == row

    def test_case_and_whitespace_variant_email_is_same_candidate(self):
        c_1001 = _candidate(
            legacy_candidate_id="C-1001",
            source="LinkedIn",
            notes="Strong React portfolio",
            email="alicia.trent@gmail.com",
        )
        c_1031 = _candidate(
            legacy_candidate_id="C-1031",
            source="Indeed",
            notes="Possible re-application",
            email="  Alicia.Trent@Gmail.com ".strip().lower(),
        )
        outcomes = deduplicate([c_1001, c_1031])
        assert len(outcomes) == 1
        assert outcomes[0].is_merge is True
        assert outcomes[0].candidate.source == "Indeed"
        assert outcomes[0].candidate.notes == "Possible re-application"

    def test_later_sparser_row_wins_even_when_it_looks_like_data_loss(self):
        c_1016 = _candidate(
            legacy_candidate_id="C-1016",
            first_name="Amara",
            last_name="Diallo",
            email="amara.diallo@gmail.com",
            phone="(917) 555-0125",
            salary_expectation="108000",
            applied_date="2026-06-04",
        )
        c_1032 = _candidate(
            legacy_candidate_id="C-1032",
            first_name="A.",
            last_name="Diallo",
            email="amara.diallo@gmail.com",
            phone="917-555-9999",
            salary_expectation="110000",
            applied_date="2026-06-20",
        )
        outcomes = deduplicate([c_1016, c_1032])
        assert len(outcomes) == 1
        merged = outcomes[0].candidate
        assert merged.first_name == "A."
        assert merged.salary_expectation == Decimal("110000")
        assert merged.applied_date == date(2026, 6, 20)

    def test_shared_legacy_id_with_different_emails_is_two_candidates(self):
        sofia = _candidate(
            legacy_candidate_id="C-1010",
            first_name="Sofía",
            last_name="Cárdenas",
            email="sofia.cardenas@hotmail.com",
            region_code="CO-BOG",
        )
        becca = _candidate(
            legacy_candidate_id="C-1010",
            first_name="Becca",
            last_name="Storm",
            email="becca.storm@gmail.com",
            region_code="US-MW",
        )
        outcomes = deduplicate([sofia, becca])
        assert len(outcomes) == 2
        assert all(not o.is_merge for o in outcomes)
        assert all(o.candidate.legacy_candidate_id == "C-1010" for o in outcomes)
        emails = {o.candidate.email for o in outcomes}
        assert emails == {"sofia.cardenas@hotmail.com", "becca.storm@gmail.com"}

    def test_preserves_first_appearance_order_of_emails(self):
        a = _candidate(email="a@gmail.com", legacy_candidate_id="A")
        b = _candidate(email="b@gmail.com", legacy_candidate_id="B")
        a2 = _candidate(email="a@gmail.com", legacy_candidate_id="A")
        outcomes = deduplicate([a, b, a2])
        assert [o.candidate.email for o in outcomes] == ["a@gmail.com", "b@gmail.com"]

    def test_empty_input_returns_empty(self):
        assert deduplicate([]) == []


class TestMergeOutcomeType:
    def test_is_a_simple_namedtuple_like_shape(self):
        outcome = MergeOutcome(candidate=_candidate(), is_merge=False)
        assert outcome.candidate.email == "alicia.trent@gmail.com"
        assert outcome.is_merge is False
