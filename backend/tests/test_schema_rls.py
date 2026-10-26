"""Database-seam tests for ticket 02: schema, app role, and RLS policy.

These connect directly to Postgres -- no FastAPI app involved -- because the
claim under test ("the region fence lives in the database, not in the
application") is unfalsifiable from the HTTP seam. See docs/adr/0002 and
spec.md ("Seams").

Fixtures connect as the *owner* role (migrations, seeding test data).
Assertions connect as `techforce_app` specifically, because RLS silently does
not apply to a table's owner or a superuser -- the one trap this ticket
exists to avoid.
"""

import subprocess
from pathlib import Path

import psycopg
import pytest

from app.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _psycopg_url(sqlalchemy_url: str) -> str:
    """psycopg.connect() wants a plain postgresql:// DSN, not the
    SQLAlchemy-style postgresql+psycopg:// driver URL."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


def _run_alembic(*args: str) -> None:
    settings = get_settings()
    subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=BACKEND_DIR,
        env={
            **__import__("os").environ,
            "ALEMBIC_TEST_DATABASE_URL": settings.test_database_url_owner,
        },
        check=True,
    )


@pytest.fixture()
def migrated_db():
    """Run migrations up on the test database, tear down afterwards."""
    _run_alembic("upgrade", "head")
    yield
    _run_alembic("downgrade", "base")


@pytest.fixture()
def owner_conn(migrated_db):
    settings = get_settings()
    conn = psycopg.connect(_psycopg_url(settings.test_database_url_owner), autocommit=True)
    yield conn
    conn.close()


@pytest.fixture()
def app_conn(migrated_db):
    settings = get_settings()
    conn = psycopg.connect(_psycopg_url(settings.test_database_url_app), autocommit=False)
    yield conn
    conn.close()


@pytest.fixture()
def seeded(owner_conn):
    """Two recruiters (one region-scoped, one admin) and three candidates."""
    with owner_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO recruiters (recruiter_id, full_name, email, is_admin)
            VALUES
                ('caleb', 'Caleb Recruiter', 'caleb@example.com', false),
                ('dana', 'Dana Admin', 'dana@example.com', true)
            """
        )
        cur.execute(
            """
            INSERT INTO recruiter_regions (recruiter_id, region_code)
            VALUES ('caleb', 'US-MW'), ('caleb', 'US-NE')
            """
        )
        cur.execute(
            """
            INSERT INTO candidates
                (email, legacy_candidate_id, first_name, last_name,
                 region_code, desired_role, status)
            VALUES
                ('a@example.com', 'C-1', 'A', 'One', 'US-MW', 'Eng', 'active'),
                ('b@example.com', 'C-2', 'B', 'Two', 'US-NE', 'Eng', 'active'),
                ('c@example.com', 'C-3', 'C', 'Three', 'PH-MNL', 'Eng', 'active')
            """
        )
    return owner_conn


def test_unset_session_setting_returns_zero_rows(app_conn, seeded):
    """Connected as techforce_app, with no recruiter identifier set, a bare
    SELECT on candidates must return zero rows -- not an error that happens
    to also return zero rows, but zero rows from the policy itself."""
    with app_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM candidates")
        (count,) = cur.fetchone()
    assert count == 0


def test_region_scoped_recruiter_sees_only_assigned_regions(app_conn, seeded):
    with app_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.recruiter_id', %s, true)", ("caleb",))
        cur.execute("SELECT region_code FROM candidates ORDER BY region_code")
        rows = {r[0] for r in cur.fetchall()}
    assert rows == {"US-MW", "US-NE"}


def test_admin_recruiter_sees_every_region(app_conn, seeded):
    with app_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.recruiter_id', %s, true)", ("dana",))
        cur.execute("SELECT region_code FROM candidates ORDER BY region_code")
        rows = {r[0] for r in cur.fetchall()}
    assert rows == {"US-MW", "US-NE", "PH-MNL"}


def test_app_role_cannot_write_via_table_ownership_bypass(app_conn, migrated_db):
    """techforce_app must not own the tables -- confirm it's not the owner,
    independent of RLS actually filtering anything."""
    with app_conn.cursor() as cur:
        cur.execute(
            "SELECT tableowner FROM pg_tables WHERE tablename = 'candidates'"
        )
        (owner,) = cur.fetchone()
    assert owner != "techforce_app"


def test_region_code_check_constraint_rejects_unknown_region(owner_conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        with owner_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO candidates
                    (email, legacy_candidate_id, first_name, last_name,
                     region_code, desired_role, status)
                VALUES ('z@example.com', 'C-9', 'Z', 'Z', 'ZZ-99', 'Eng', 'active')
                """
            )


def test_status_check_constraint_rejects_unknown_status(owner_conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        with owner_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO candidates
                    (email, legacy_candidate_id, first_name, last_name,
                     region_code, desired_role, status)
                VALUES ('y@example.com', 'C-8', 'Y', 'Y', 'US-W', 'Eng', 'bogus')
                """
            )


def test_candidate_email_unique_constraint(owner_conn):
    with owner_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidates
                (email, legacy_candidate_id, first_name, last_name,
                 region_code, desired_role, status)
            VALUES ('dup@example.com', 'C-1', 'D', 'One', 'US-W', 'Eng', 'active')
            """
        )
    with pytest.raises(psycopg.errors.UniqueViolation):
        with owner_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO candidates
                    (email, legacy_candidate_id, first_name, last_name,
                     region_code, desired_role, status)
                VALUES ('dup@example.com', 'C-2', 'D', 'Two', 'US-W', 'Eng', 'active')
                """
            )


def test_legacy_candidate_id_not_unique(owner_conn):
    """Two different Candidates may share a Legacy Candidate ID -- it is
    retained for traceability only, never identity. See ADR 0001."""
    with owner_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidates
                (email, legacy_candidate_id, first_name, last_name,
                 region_code, desired_role, status)
            VALUES
                ('p1@example.com', 'C-1010', 'P', 'One', 'US-W', 'Eng', 'active'),
                ('p2@example.com', 'C-1010', 'P', 'Two', 'US-W', 'Eng', 'active')
            """
        )
        cur.execute(
            "SELECT count(*) FROM candidates WHERE legacy_candidate_id = 'C-1010'"
        )
        (count,) = cur.fetchone()
    assert count == 2
