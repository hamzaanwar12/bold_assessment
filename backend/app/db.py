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
from app.schemas import Candidate, CandidateListPage, CandidateOut

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


def _set_recruiter_scope(cur: psycopg.Cursor, recruiter_id: str) -> None:
    """Bind the RLS policy's recruiter for this transaction.

    One helper on purpose: this is the single line the whole authorization
    model rests on, and it must stay a BOUND PARAMETER. `set_config(..., true)`
    is transaction-local and parameterizable; interpolating the id into a `SET`
    statement would reintroduce injection at exactly the point the security
    model depends on (ADR 0002). Two copies of this is two chances to get it
    wrong.
    """
    cur.execute("SELECT set_config('app.recruiter_id', %s, true)", (recruiter_id,))


# PostgreSQL's hard limit is 65535 bind parameters per statement.
_MAX_ROWS_PER_STATEMENT = 65535 // len(_FIELDS)


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
        _set_recruiter_scope(cur, recruiter_id)

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
                # New to the database and folded from several Source Rows:
                # the FIRST row created the Candidate (an Import) and each
                # extra row folded into it (a Merge). Crediting only the
                # Merges loses the first row, and then the report no longer
                # accounts for its input -- imported + merged + rejected
                # must equal the number of Source Rows.
                imported += 1
                merged += outcome.merged_rows

        placeholder_row = "(" + ", ".join(["%s"] * len(_FIELDS)) + ")"
        set_clause = ", ".join(f"{field} = EXCLUDED.{field}" for field in _FIELDS if field != "email")

        # PostgreSQL allows at most 65535 bind parameters per statement, so a
        # single VALUES list cannot hold an unbounded number of rows. Chunk by
        # that limit rather than row count, and keep every chunk inside the
        # caller's one transaction so the import stays all-or-nothing.
        for start in range(0, len(finals), _MAX_ROWS_PER_STATEMENT):
            chunk = finals[start : start + _MAX_ROWS_PER_STATEMENT]
            params: list[object] = []
            for candidate in chunk:
                for field in _FIELDS:
                    value = getattr(candidate, field)
                    if value is None and field in _NOT_NULL_TEXT_FIELDS:
                        value = ""
                    params.append(value)

            cur.execute(
                f"""
                INSERT INTO candidates ({", ".join(_FIELDS)})
                VALUES {", ".join([placeholder_row] * len(chunk))}
                ON CONFLICT (email) DO UPDATE SET
                    {set_clause},
                    updated_at = now()
                """,
                params,
            )

    return imported, merged


# Column order for the read path -- `id` plus every field the Import write
# path already knows how to serialize. One repository function (this one)
# is the only Candidate read path in application code (ticket 07; spec.md
# "API contract"; docs/adr/0002, "a single repository function remains the
# only read path"): the router builds no query of its own.
_LIST_FIELDS = ("id", *_FIELDS)




def list_candidates(
    conn: psycopg.Connection,
    recruiter_id: str,
    *,
    search: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> CandidateListPage:
    """Return one page of Candidates, scoped to `recruiter_id`'s Assigned
    Regions by the RLS policy on `candidates` (docs/adr/0002).

    Sets `app.recruiter_id` via `set_config(..., true)` (`SET LOCAL`
    semantics), bound as a parameter -- never interpolated -- then runs the
    `COUNT` and the page `SELECT` in the SAME transaction the caller already
    opened, so both are fenced by the identical RLS context. Computing
    `total` outside this transaction (or on a second connection) would leak
    the global Candidate count while `items` still looked correctly scoped
    -- the specific trap ticket 07 calls out.

    `ORDER BY id` gives pagination a deterministic order; without one,
    PostgreSQL may return rows in a different order across two queries and
    page 2 can repeat or skip rows.
    """
    with conn.cursor() as cur:
        _set_recruiter_scope(cur, recruiter_id)

        where_clauses: list[str] = []
        params: list[object] = []
        if search:
            where_clauses.append(
                "(first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s OR desired_role ILIKE %s)"
            )
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern, pattern])
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cur.execute(f"SELECT count(*) FROM candidates {where_sql}", params)
        (total,) = cur.fetchone()

        offset = (page - 1) * page_size
        cur.execute(
            f"""
            SELECT {", ".join(_LIST_FIELDS)} FROM candidates
            {where_sql}
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            [*params, page_size, offset],
        )
        columns = [desc[0] for desc in cur.description]
        # model_construct, not model_validate: these values are already
        # normalized and typed by the database (same reasoning as
        # `_candidate_from_row` above) -- re-running the Candidate
        # validators on an already-Decimal salary or already-date
        # applied_date raises, since the normalizers expect raw strings.
        items = [CandidateOut.model_construct(**dict(zip(columns, row))) for row in cur.fetchall()]

    return CandidateListPage(items=items, total=total, page=page, page_size=page_size)
