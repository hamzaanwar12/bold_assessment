"""Shared FastAPI dependencies: which database connection the app uses, and
who is asking.

`get_app_dsn` is a dependency -- not a bare module function -- for exactly
one reason: it is the single override point a test uses to point the app at
the test database instead of production. Nothing else in the app should
construct a DSN independently (see docs/adr/0002: the API must never
connect as the owner role).

`resolve_recruiter` answers "who is asking" from the Recruiter identifier
header, against the `recruiters` table, before any Candidate query is
constructed -- an unknown identifier is a `403`, never an empty result that
would look like "no Candidates" (spec.md: API contract).
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from fastapi import Depends, Header, HTTPException

from app.settings import get_settings

RECRUITER_ID_HEADER = "X-Recruiter-Id"


def _psycopg_url(sqlalchemy_url: str) -> str:
    """psycopg.connect() wants a plain postgresql:// DSN, not the
    SQLAlchemy-style postgresql+psycopg:// driver URL."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


def get_app_dsn() -> str:
    """The application role's connection string: `techforce_app`, never the
    owner. RLS does not apply to a table's owner -- see docs/adr/0002."""
    return _psycopg_url(get_settings().database_url_app)


@dataclass(frozen=True)
class Recruiter:
    """The authenticated caller: a Recruiter identifier and whether they are
    an Admin (GLOSSARY.md: Recruiter, Admin)."""

    recruiter_id: str
    is_admin: bool


def resolve_recruiter(
    x_recruiter_id: str | None = Header(default=None, alias=RECRUITER_ID_HEADER),
    dsn: str = Depends(get_app_dsn),
) -> Recruiter:
    if not x_recruiter_id:
        raise HTTPException(status_code=403, detail=f"{RECRUITER_ID_HEADER} header is required")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM recruiters WHERE recruiter_id = %s", (x_recruiter_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="unknown Recruiter identifier")
    (is_admin,) = row
    return Recruiter(recruiter_id=x_recruiter_id, is_admin=is_admin)


def require_admin(recruiter: Recruiter = Depends(resolve_recruiter)) -> Recruiter:
    """Import is Admin-only (inferred decision, spec.md: API contract):
    a Region-scoped Recruiter must not write global Candidate data."""
    if not recruiter.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return recruiter
