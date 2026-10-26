"""Shared fixtures for the Import endpoint tests (ticket 06).

Module-scoped migration (one `alembic upgrade`/`downgrade` per test module,
not per test -- the suite-wide migrate-per-test pattern in
test_schema_rls.py is kept local to that file) with a `TRUNCATE` between
tests, so each test starts from an empty, migrated schema without paying
for a full up/down cycle every time.

A test file that defines its own fixture of the same name (test_schema_rls.py,
test_seed.py) shadows these for that module -- pytest fixture resolution
prefers the closer scope -- so adding these here does not change their
behaviour.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

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


@pytest.fixture(scope="module")
def migrated_db():
    _run_alembic("upgrade", "head")
    yield
    _run_alembic("downgrade", "base")


@pytest.fixture()
def owner_conn(migrated_db):
    settings = get_settings()
    conn = psycopg.connect(_psycopg_url(settings.test_database_url_owner), autocommit=True)
    yield conn
    with conn.cursor() as cur:
        cur.execute("TRUNCATE candidates, recruiter_regions, recruiters CASCADE")
    conn.close()


@pytest.fixture()
def test_app_dsn() -> str:
    return _psycopg_url(get_settings().test_database_url_app)
