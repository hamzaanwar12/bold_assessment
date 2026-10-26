"""Tests for the idempotent Recruiter-seeding command (ticket 03).

Seeding is not a Candidate read, so it runs as the owner role, which bypasses
RLS entirely -- see docs/adr/0002 ("Consequences"). These tests therefore
connect as the owner, same as the fixtures in test_schema_rls.py.
"""

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

from app import seed
from app.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _psycopg_url(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


def _run_alembic(*args: str) -> None:
    settings = get_settings()
    subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "ALEMBIC_TEST_DATABASE_URL": settings.test_database_url_owner},
        check=True,
    )


@pytest.fixture()
def migrated_db():
    _run_alembic("upgrade", "head")
    yield
    _run_alembic("downgrade", "base")


@pytest.fixture()
def owner_conn(migrated_db):
    settings = get_settings()
    conn = psycopg.connect(_psycopg_url(settings.test_database_url_owner), autocommit=False)
    yield conn
    conn.close()


def _counts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM recruiters")
        (recruiters,) = cur.fetchone()
        cur.execute("SELECT count(*) FROM recruiter_regions")
        (regions,) = cur.fetchone()
    return recruiters, regions


def _regions_for(conn, recruiter_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT region_code FROM recruiter_regions WHERE recruiter_id = %s ORDER BY region_code",
            (recruiter_id,),
        )
        return [r[0] for r in cur.fetchall()]


def test_seed_loads_five_recruiters_with_expected_regions(owner_conn):
    seed.seed(owner_conn)
    owner_conn.commit()

    with owner_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM recruiters")
        (count,) = cur.fetchone()
    assert count == 5

    with owner_conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM recruiters WHERE recruiter_id = 'R-101'")
        (is_admin,) = cur.fetchone()
    assert is_admin is True
    assert _regions_for(owner_conn, "R-101") == []

    assert _regions_for(owner_conn, "R-102") == ["US-MW", "US-NE"]
    assert _regions_for(owner_conn, "R-103") == ["CO-BOG", "PH-MNL"]
    assert _regions_for(owner_conn, "R-104") == ["US-SE", "US-W"]
    assert _regions_for(owner_conn, "R-105") == ["US-NE"]


def test_seed_is_idempotent(owner_conn):
    seed.seed(owner_conn)
    owner_conn.commit()
    before = _counts(owner_conn)

    seed.seed(owner_conn)
    owner_conn.commit()
    after = _counts(owner_conn)

    assert before == after == (5, 2 + 2 + 2 + 1)
    assert _regions_for(owner_conn, "R-103") == ["CO-BOG", "PH-MNL"]
