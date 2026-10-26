"""The write path: batching deduplicated Candidates into one upsert.

Owned by ticket 06. Pure with respect to HTTP -- takes an open `psycopg`
connection and the already-deduplicated-in-memory outcomes from
`app.dedup.deduplicate`, and performs exactly one multi-row `INSERT ...
ON CONFLICT ... DO UPDATE` inside the caller's transaction. No per-row
insert in a loop (spec.md: Import pipeline, phase 4).

Folds each in-memory outcome against any Candidate already in the database
under the same Normalized Email, via the same `merge_candidate` seam
`app.dedup.deduplicate` uses -- so a re-upload of an already-imported row
counts as a Merge, not a second Import (ADR 0001; GLOSSARY.md: Merge).

Sets `app.recruiter_id` to the (Admin) caller's identifier for this
transaction via `set_config(..., true)`, bound as a parameter -- never
interpolated into a `SET` statement. The RLS policy on `candidates` is
`FOR ALL` with no explicit `WITH CHECK`, so it constrains this INSERT too;
only its Admin branch permits writing across every Region, which is why
Import is Admin-only in the application as well (docs/adr/0002,
"Consequences").
"""

from __future__ import annotations

import psycopg

from app.dedup import MergeOutcome, merge_candidate
from app.schemas import Candidate

# Column order shared by the SELECT (to rehydrate existing Candidates) and
# the INSERT (to write the folded result). One list, so the two statements
# can never silently drift apart.
_FIELDS = (
    "legacy_candidate_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "region_code",
    "desired_role",
    "salary_expectation",
    "applied_date",
    "status",
    "source",
    "notes",
)

# `candidates.first_name`, `last_name`, and `desired_role` are NOT NULL in
# the schema (ec549ae439ff), but the Candidate schema (ticket 04) allows
# them to be absent -- a missing name or desired role is not identity- or
# authorization-bearing, so it is not a Rejection. Fill with "" at the
# database boundary only; the Candidate value itself stays None.
_NOT_NULL_TEXT_FIELDS = frozenset({"first_name", "last_name", "desired_role"})


def _candidate_from_row(row: dict[str, object]) -> Candidate:
    """Rebuild a Candidate from a database row without re-running
    normalization -- the stored values are already normalized and typed."""
    return Candidate.model_construct(**row)


def write_import(
    conn: psycopg.Connection, recruiter_id: str, outcomes: list[MergeOutcome]
) -> tuple[int, int]:
    """Write `outcomes` in one batch, inside the caller's transaction.

    Returns `(imported, merged)` counts by Source Row (GLOSSARY.md: Import
    Outcome) -- not by Normalized Email: an email folded from several
    Source Rows is one Import plus one Merge per extra row, and an email
    that already existed in the database is a Merge regardless of how many
    Source Rows fed it in this Import.

    Does not commit or roll back -- that is the caller's transaction
    boundary, so a database error here propagates and the whole batch is
    undone.
    """
    if not outcomes:
        return (0, 0)

    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.recruiter_id', %s, true)", (recruiter_id,))

        emails = [outcome.candidate.email for outcome in outcomes]
        cur.execute(
            f"SELECT {', '.join(_FIELDS)} FROM candidates WHERE email = ANY(%s)",
            (emails,),
        )
        existing_by_email: dict[str, Candidate] = {}
        for raw_row in cur.fetchall():
            row = dict(zip(_FIELDS, raw_row))
            existing_by_email[row["email"]] = _candidate_from_row(row)

        imported = 0
        merged = 0
        finals: list[Candidate] = []
        for outcome in outcomes:
            existing = existing_by_email.get(outcome.candidate.email)
            finals.append(merge_candidate(existing, outcome.candidate))
            if existing is not None:
                # The identity already existed before this Import: every
                # Source Row that fed this outcome is a Merge.
                merged += 1 + outcome.merged_rows
            elif outcome.merged_rows == 0:
                imported += 1
            else:
                # New to the database, but folded from more than one
                # Source Row within this Import: the extra rows are
                # Merges (ADR 0001 / app.dedup), matching how `deduplicate`
                # itself reports a single Normalized Email's outcome.
                merged += outcome.merged_rows

        placeholder_row = "(" + ", ".join(["%s"] * len(_FIELDS)) + ")"
        values_sql = ", ".join([placeholder_row] * len(finals))
        set_clause = ", ".join(f"{field} = EXCLUDED.{field}" for field in _FIELDS if field != "email")

        params: list[object] = []
        for candidate in finals:
            for field in _FIELDS:
                value = getattr(candidate, field)
                if value is None and field in _NOT_NULL_TEXT_FIELDS:
                    value = ""
                params.append(value)

        cur.execute(
            f"""
            INSERT INTO candidates ({", ".join(_FIELDS)})
            VALUES {values_sql}
            ON CONFLICT (email) DO UPDATE SET
                {set_clause},
                updated_at = now()
            """,
            params,
        )

    return imported, merged
