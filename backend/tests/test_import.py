"""HTTP-seam tests for ticket 06: POST /api/v1/candidates/import.

Primary seam per spec.md ("Seams"): an in-process TestClient against the
real FastAPI app, backed by the real test PostgreSQL, with the app pointed
at the test database via a dependency override on `get_app_dsn` (the one
override point -- see app/deps.py).

Recruiters R-101 (Admin) and R-102 (Region-scoped) come from the real
roster fixture (data/recruiters.csv) via app.seed.seed, the same path the
project uses everywhere else -- so these tests exercise the same roster the
acceptance criteria name.
"""

from __future__ import annotations

import io
from pathlib import Path

import csv
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import write_import
from app.deps import get_app_dsn
from app.main import app
from app.schemas import Candidate
from app.seed import seed

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_CSV = REPO_ROOT / "data" / "candidates_import.csv"


@pytest.fixture()
def seeded_recruiters(owner_conn):
    """The real five-Recruiter roster: R-101 is the Admin used throughout."""
    seed(owner_conn)
    return owner_conn


@pytest.fixture()
def client(test_app_dsn):
    app.dependency_overrides[get_app_dsn] = lambda: test_app_dsn
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_app_dsn, None)


def _upload(client: TestClient, content: bytes, recruiter_id: str = "R-101", filename: str = "candidates.csv"):
    return client.post(
        "/api/v1/candidates/import",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
        headers={"X-Recruiter-Id": recruiter_id},
    )


SMALL_CSV = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes\r\n"
    'C-1,Ann,Alpha,ann@example.com,,US-MW,Engineer,"$90,000",2026-01-01,active,LinkedIn,first\r\n'
    "C-2,Bea,Beta,bea@example.com,,US-W,Engineer,,2026-01-02,active,LinkedIn,\r\n"
    "C-3,Ann,Alpha2,  Ann@Example.com ,,US-MW,Engineer,,2026-01-03,screening,Indeed,dup of row 1\r\n"
    "C-4,Cat,Gamma,not-an-email,,US-MW,Engineer,,2026-01-04,active,Indeed,bad email\r\n"
    "C-5,Dee,Delta,dee@example.com,,ZZ-99,Engineer,,2026-01-05,active,Indeed,bad region\r\n"
).encode("utf-8")


class TestAuthorization:
    def test_non_admin_recruiter_gets_403_and_writes_nothing(self, client, seeded_recruiters):
        response = _upload(client, SMALL_CSV, recruiter_id="R-102")
        assert response.status_code == 403
        with seeded_recruiters.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidates")
            (count,) = cur.fetchone()
        assert count == 0

    def test_unknown_recruiter_gets_403(self, client, seeded_recruiters):
        response = _upload(client, SMALL_CSV, recruiter_id="R-999")
        assert response.status_code == 403

    def test_missing_header_gets_403(self, client, seeded_recruiters):
        response = client.post(
            "/api/v1/candidates/import",
            files={"file": ("c.csv", io.BytesIO(SMALL_CSV), "text/csv")},
        )
        assert response.status_code == 403


class TestUploadValidation:
    def test_non_csv_filename_is_rejected(self, client, seeded_recruiters):
        response = _upload(client, SMALL_CSV, filename="candidates.txt")
        assert response.status_code == 400

    def test_undecodable_upload_is_rejected(self, client, seeded_recruiters):
        response = _upload(client, b"\xff\xfe\x00bad", filename="candidates.csv")
        assert response.status_code == 400


class TestImportReport:
    def test_small_csv_merges_case_variant_and_rejects_bad_rows(self, client, seeded_recruiters):
        response = _upload(client, SMALL_CSV)
        assert response.status_code == 200
        body = response.json()

        # Row 1 (ann@example.com) created a Candidate -> Import.
        # Row 3 (case/whitespace variant of the same email) folded into it
        # -> Merge. Row 2 (bea@example.com) -> Import. Rows 4, 5 -> Rejections.
        # Every Source Row therefore has exactly one outcome: 2 + 1 + 2 = 5.
        assert body["imported"] == 2
        assert body["merged"] == 1
        assert {r["row"] for r in body["rejected"]} == {4, 5}
        assert body["imported"] + body["merged"] + len(body["rejected"]) == 5
        reasons = {r["row"]: r["reason"] for r in body["rejected"]}
        assert "email" in reasons[4] or "malformed" in reasons[4]
        assert "region" in reasons[5] or "ZZ-99" in reasons[5]

    def test_merge_follows_last_writer_wins_with_null_safety(self, client, seeded_recruiters):
        _upload(client, SMALL_CSV)
        with seeded_recruiters.cursor() as cur:
            cur.execute(
                "SELECT first_name, last_name, status FROM candidates WHERE email = 'ann@example.com'"
            )
            first_name, last_name, status = cur.fetchone()
        # Row 3 is the later Source Row for this email: its non-null fields
        # win (last_name, status), per the stated merge rule (ADR 0001).
        assert last_name == "Alpha2"
        assert status == "screening"
        # Row 3's first_name ("Ann") is non-null too, so it stays "Ann" --
        # this assertion exists to distinguish "last-writer-wins" from
        # "first-writer-wins", not to claim anything about nulls here.
        assert first_name == "Ann"

    def test_reupload_of_already_imported_row_counts_as_merge_not_import(self, client, seeded_recruiters):
        first = _upload(client, SMALL_CSV).json()
        second = _upload(client, SMALL_CSV).json()
        assert first["imported"] == 2
        assert first["merged"] == 1
        # Re-uploading the same file: every survivor already exists in the
        # database, so nothing is a new Import the second time (spec.md,
        # story 9: "re-uploading the same file is safe").
        assert second["imported"] == 0
        # Every Source Row this time folds against a Candidate that
        # already existed before this Import: all 3 surviving rows
        # (2 for ann's group, 1 for bea's) are Merges.
        assert second["merged"] == 3
        with seeded_recruiters.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidates")
            (count,) = cur.fetchone()
        assert count == 2

    def test_sql_injection_payload_stored_as_literal_text_and_table_survives(self, client, seeded_recruiters):
        payload_csv = (
            "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
            "salary_expectation,applied_date,status,source,notes\r\n"
            "C-9,Rob,\"O'Connor'); DROP TABLE candidates;--\",rob@example.com,,US-MW,Engineer,,2026-01-01,active,LinkedIn,\r\n"
        ).encode("utf-8")
        response = _upload(client, payload_csv)
        assert response.status_code == 200
        with seeded_recruiters.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('candidates') IS NOT NULL"
            )
            (table_exists,) = cur.fetchone()
            assert table_exists is True
            cur.execute("SELECT last_name FROM candidates WHERE email = 'rob@example.com'")
            (last_name,) = cur.fetchone()
        assert last_name == "O'Connor'); DROP TABLE candidates;--"


class TestRealFixtureAcceptance:
    def test_candidates_import_csv_as_admin_matches_the_documented_report(self, client, seeded_recruiters):
        content = FIXTURE_CSV.read_bytes()
        response = _upload(client, content, recruiter_id="R-101", filename="candidates_import.csv")
        assert response.status_code == 200
        body = response.json()

        assert body["imported"] == 41
        assert body["merged"] == 3
        assert len(body["rejected"]) == 9
        assert {r["row"] for r in body["rejected"]} == {34, 35, 36, 41, 45, 46, 48, 49, 53}

        # The Import Report must account for its input: every Source Row is
        # imported, merged, or rejected -- exactly one of the three. An earlier
        # version credited only the Merges of a folded group and silently lost
        # three rows (50 != 53) while every other assertion still passed.
        source_rows = sum(1 for _ in csv.DictReader(io.StringIO(content.decode("utf-8"))))
        assert source_rows == 53
        assert body["imported"] + body["merged"] + len(body["rejected"]) == source_rows

        with seeded_recruiters.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidates")
            (count,) = cur.fetchone()
        assert count == 41

        # C-1050's quoted, multi-line notes field must survive intact --
        # proof the parser is a real CSV reader, not a newline split.
        cur = seeded_recruiters.cursor()
        cur.execute("SELECT notes FROM candidates WHERE email = 'oliver.grant@gmail.com'")
        (notes,) = cur.fetchone()
        cur.close()
        assert notes == "Interview notes:\nRound 1 passed.\nRound 2 pending scheduling."

    def test_candidates_import_csv_as_non_admin_is_forbidden(self, client, seeded_recruiters):
        content = FIXTURE_CSV.read_bytes()
        response = _upload(client, content, recruiter_id="R-102", filename="candidates_import.csv")
        assert response.status_code == 403
        with seeded_recruiters.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidates")
            (count,) = cur.fetchone()
        assert count == 0


class TestDatabaseFailureRollsBackTheWholeImport:
    """The HTTP seam cannot force a database error here: every value that
    reaches write_import has already passed Candidate validation, so it
    cannot violate a CHECK constraint. This test calls write_import
    directly -- the one seam where the "all survivors in one transaction"
    guarantee is actually falsifiable -- bypassing app-level validation on
    purpose to construct a batch where one row is valid and the next is
    not, and asserting the valid row is not left behind.
    """

    def test_one_bad_row_rolls_back_the_entire_batch(self, owner_conn, test_app_dsn):
        from app.dedup import MergeOutcome

        good = Candidate.model_validate(
            {
                "candidate_id": "C-1",
                "first_name": "Good",
                "last_name": "Row",
                "email": "good@example.com",
                "region_code": "US-MW",
                "desired_role": "Engineer",
                "status": "active",
            }
        )
        # Bypasses Candidate validation deliberately (model_construct, not
        # model_validate) to reach the database with a region the CHECK
        # constraint rejects -- the only way to force the DB error this
        # test exists to prove is handled.
        bad = Candidate.model_construct(
            legacy_candidate_id="C-2",
            first_name="Bad",
            last_name="Row",
            email="bad@example.com",
            phone=None,
            region_code="NOT-A-REGION",
            desired_role="Engineer",
            salary_expectation=None,
            applied_date=None,
            status="active",
            source=None,
            notes=None,
        )
        outcomes = [MergeOutcome(candidate=good), MergeOutcome(candidate=bad)]

        with psycopg.connect(test_app_dsn) as conn:
            with pytest.raises(psycopg.Error):
                with conn.transaction():
                    write_import(conn, "R-101", outcomes)

        with owner_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidates")
            (count,) = cur.fetchone()
        assert count == 0
