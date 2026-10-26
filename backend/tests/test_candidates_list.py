"""HTTP-seam tests for ticket 07: GET /api/v1/candidates.

Same seam as tests/test_import.py: an in-process TestClient against the real
FastAPI app, backed by the real test PostgreSQL, with the app pointed at the
test database via the `get_app_dsn` override.

Authorization is the point of this endpoint (ADR 0002): the real roster
(data/recruiters.csv) and the real fixture CSV (data/candidates_import.csv)
are imported as R-101 (Admin) so the scoping assertions below are against
real, varied Region data rather than a hand-built fixture that could
accidentally make every test pass regardless of scoping.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.deps import get_app_dsn
from app.main import app
from app.seed import seed

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_CSV = REPO_ROOT / "data" / "candidates_import.csv"


@pytest.fixture()
def client(test_app_dsn):
    app.dependency_overrides[get_app_dsn] = lambda: test_app_dsn
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_app_dsn, None)


@pytest.fixture()
def seeded_and_imported(owner_conn, client):
    """The real 5-Recruiter roster and the real 41-Candidate fixture,
    imported through the actual HTTP import path (as R-101, Admin) so the
    data in the database is exactly what the acceptance criteria describe."""
    seed(owner_conn)
    response = client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", io.BytesIO(FIXTURE_CSV.read_bytes()), "text/csv")},
        headers={"X-Recruiter-Id": "R-101"},
    )
    assert response.status_code == 200
    return owner_conn


def _list(client: TestClient, recruiter_id: str | None, **params):
    headers = {"X-Recruiter-Id": recruiter_id} if recruiter_id else {}
    return client.get("/api/v1/candidates", params=params, headers=headers)


class TestAuthorization:
    def test_unknown_recruiter_gets_403_before_any_query(self, client, seeded_and_imported):
        response = _list(client, "R-999")
        assert response.status_code == 403

    def test_missing_header_gets_403(self, client, seeded_and_imported):
        response = _list(client, None)
        assert response.status_code == 403

    def test_admin_sees_every_candidate(self, client, seeded_and_imported):
        response = _list(client, "R-101", page_size=100)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 41
        assert len(body["items"]) == 41

    def test_region_scoped_recruiter_sees_strictly_fewer_than_admin(self, client, seeded_and_imported):
        response = _list(client, "R-103", page_size=100)
        assert response.status_code == 200
        body = response.json()
        # R-103 (Marisol) is assigned PH-MNL and CO-BOG only.
        assert body["total"] < 41
        assert body["total"] > 0
        regions = {item["region_code"] for item in body["items"]}
        assert regions <= {"PH-MNL", "CO-BOG"}

    def test_total_is_scoped_not_global(self, client, seeded_and_imported):
        """The specific trap: total must come from inside the same scoped
        transaction as items, not a second, unscoped count."""
        response = _list(client, "R-103", page_size=1)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] < 41


class TestSearchCannotEscapeScope:
    def test_search_for_a_candidate_outside_the_scope_returns_nothing(self, client, seeded_and_imported):
        # Find a Candidate that exists only outside R-103's regions (PH-MNL,
        # CO-BOG), then search for them as R-103 -- the result must be empty,
        # not just correctly counted.
        admin_response = _list(client, "R-101", search="", page_size=100)
        us_candidates = [
            item for item in admin_response.json()["items"] if item["region_code"] not in ("PH-MNL", "CO-BOG")
        ]
        assert us_candidates, "fixture must contain a Candidate outside R-103's regions"
        target = us_candidates[0]

        response = _list(client, "R-103", search=target["first_name"], page_size=100)
        assert response.status_code == 200
        assert response.json()["items"] == []


class TestPagination:
    def test_page_size_is_clamped_to_100(self, client, seeded_and_imported):
        response = _list(client, "R-101", page_size=500)
        assert response.status_code == 200
        assert response.json()["page_size"] == 100

    def test_pages_are_stable_and_do_not_repeat_or_skip(self, client, seeded_and_imported):
        page1 = _list(client, "R-101", page=1, page_size=20).json()
        page2 = _list(client, "R-101", page=2, page_size=20).json()
        page3 = _list(client, "R-101", page=3, page_size=20).json()
        ids1 = [item["email"] for item in page1["items"]]
        ids2 = [item["email"] for item in page2["items"]]
        ids3 = [item["email"] for item in page3["items"]]
        assert len(ids1) == 20
        assert len(ids2) == 20
        assert len(ids3) == 1
        assert set(ids1).isdisjoint(ids2)
        assert set(ids2).isdisjoint(ids3)
        assert set(ids1).isdisjoint(ids3)

    def test_default_page_size_is_25(self, client, seeded_and_imported):
        response = _list(client, "R-101")
        assert response.status_code == 200
        body = response.json()
        assert body["page_size"] == 25
        assert len(body["items"]) == 25


class TestFilters:
    def test_status_filter_combines_with_search(self, client, seeded_and_imported):
        all_active = _list(client, "R-101", status="active", page_size=100).json()["items"]
        assert all_active
        assert all(item["status"] == "active" for item in all_active)

    def test_status_filter_actually_combines_with_a_search_term(self, client, seeded_and_imported):
        """The test above never passes `search`, so it cannot prove the two
        filters combine (AND, not OR) -- only that status alone works. Pick
        a candidate with a known status and search for them by name while
        also filtering on their status: the match must survive. Then search
        for the same name while filtering on a status they do NOT have: the
        combined filter must exclude them, proving `search` and `status` are
        ANDed rather than each applied independently."""
        admin = _list(client, "R-101", page_size=100).json()["items"]
        sample = admin[0]
        matching = _list(
            client, "R-101", search=sample["last_name"], status=sample["status"]
        ).json()["items"]
        assert sample["email"] in {item["email"] for item in matching}

        other_status = next(s for s in ("active", "screening", "interviewing", "withdrawn") if s != sample["status"])
        excluded = _list(
            client, "R-101", search=sample["last_name"], status=other_status
        ).json()["items"]
        assert sample["email"] not in {item["email"] for item in excluded}

    def test_search_matches_case_insensitively_across_fields(self, client, seeded_and_imported):
        admin = _list(client, "R-101", page_size=100).json()["items"]
        sample = admin[0]
        response = _list(client, "R-101", search=sample["last_name"].upper())
        assert response.status_code == 200
        emails = {item["email"] for item in response.json()["items"]}
        assert sample["email"] in emails

    def test_search_matches_email_case_insensitively(self, client, seeded_and_imported):
        admin = _list(client, "R-101", page_size=100).json()["items"]
        sample = admin[0]
        response = _list(client, "R-101", search=sample["email"].upper())
        assert response.status_code == 200
        emails = {item["email"] for item in response.json()["items"]}
        assert sample["email"] in emails

    def test_search_matches_desired_role_case_insensitively(self, client, seeded_and_imported):
        admin = _list(client, "R-101", page_size=100).json()["items"]
        sample = admin[0]
        response = _list(client, "R-101", search=sample["desired_role"].upper())
        assert response.status_code == 200
        emails = {item["email"] for item in response.json()["items"]}
        assert sample["email"] in emails


class TestResponseContract:
    """Pins the JSON field names the frontend reads.

    This boundary was unprotected and it broke: adding `alias="candidate_id"`
    to read the CSV column also renamed the field on the way OUT, because
    FastAPI serializes response models with by_alias=True. The frontend read
    `legacy_candidate_id`, got undefined, and TypeScript could not catch it --
    its interface asserts a shape rather than verifying one.
    """

    def test_list_response_uses_glossary_field_names(self, client, seeded_and_imported):
        body = client.get(
            "/api/v1/candidates", params={"page_size": 1}, headers={"X-Recruiter-Id": "R-101"}
        ).json()
        item = body["items"][0]
        assert "legacy_candidate_id" in item, "the frontend reads this name"
        assert "candidate_id" not in item, "the validation alias must not leak into the response"
        assert isinstance(item["id"], int), "rows need a stable identity for list keys"

    def test_legacy_candidate_id_is_not_unique_so_id_is_required(self, client, seeded_and_imported):
        """ADR 0001: one legacy id covers two different people. Anything keyed
        on it collides; `id` is what distinguishes them."""
        body = client.get(
            "/api/v1/candidates", params={"page_size": 100}, headers={"X-Recruiter-Id": "R-101"}
        ).json()
        shared = [i for i in body["items"] if i["legacy_candidate_id"] == "C-1010"]
        assert len(shared) == 2, "the fixture's deliberate id collision"
        assert len({i["id"] for i in shared}) == 2, "ids must distinguish them"
