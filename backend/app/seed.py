"""Idempotent seed command for the Recruiter roster (ticket 03).

Loads `data/recruiters.csv` into `recruiters` / `recruiter_regions`. `*` in
`assigned_regions` sets the Admin flag (GLOSSARY.md: Admin); an Admin gets no
`recruiter_regions` rows at all, because an Admin's visibility does not
depend on that table (GLOSSARY.md: Assigned Regions).

Must run as the owner connection, never the application role: seeding the
roster is not a Candidate read, so it should not be subject to the RLS
policy -- see docs/adr/0002 ("Consequences").
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import psycopg

from app.settings import get_settings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO_ROOT / "data" / "recruiters.csv"


def _psycopg_url(sqlalchemy_url: str) -> str:
    """psycopg.connect() wants a plain postgresql:// DSN, not the
    SQLAlchemy-style postgresql+psycopg:// driver URL."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


def load_rows(csv_path: Path = CSV_PATH) -> list[dict[str, Any]]:
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def seed(conn: psycopg.Connection, rows: list[dict[str, Any]] | None = None) -> None:
    """Upsert the Recruiter roster. Idempotent: running twice leaves the same
    rows in `recruiters` and `recruiter_regions`, with no duplicates.

    Does not commit -- callers control the transaction boundary.
    """
    rows = rows if rows is not None else load_rows()
    with conn.cursor() as cur:
        for row in rows:
            recruiter_id = row["recruiter_id"]
            full_name = row["full_name"]
            email = row["email"]
            assigned_regions = row["assigned_regions"].strip()
            is_admin = assigned_regions == "*"

            cur.execute(
                """
                INSERT INTO recruiters (recruiter_id, full_name, email, is_admin)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (recruiter_id) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    email = EXCLUDED.email,
                    is_admin = EXCLUDED.is_admin
                """,
                (recruiter_id, full_name, email, is_admin),
            )

            # Recompute this Recruiter's regions from the fixture every run,
            # rather than inserting blindly -- that is what keeps a second
            # run from creating duplicates (or leaving stale regions behind
            # after a roster edit). An Admin gets none.
            cur.execute(
                "DELETE FROM recruiter_regions WHERE recruiter_id = %s",
                (recruiter_id,),
            )
            if not is_admin:
                regions = [r.strip() for r in assigned_regions.split("|") if r.strip()]
                cur.executemany(
                    "INSERT INTO recruiter_regions (recruiter_id, region_code) VALUES (%s, %s)",
                    [(recruiter_id, region) for region in regions],
                )


def main() -> None:
    settings = get_settings()
    with psycopg.connect(_psycopg_url(settings.database_url_owner)) as conn:
        seed(conn)
        conn.commit()


if __name__ == "__main__":
    main()
