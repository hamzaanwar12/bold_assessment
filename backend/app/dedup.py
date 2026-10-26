"""Deduplication and merge over already-validated Candidates.

Pure in-memory logic: no database, no endpoint (those belong to a later
ticket). Operates on `app.schemas.Candidate` instances produced by
validation, grouping Source Rows by Normalized Email and folding each group
into a single Candidate per the merge rule in ADR 0001 / spec.md
("Identity and deduplication").

The merge rule, stated once, applied everywhere:

    Last-writer-wins by Source Row order, with one override — a null/None
    value never overwrites a non-null value.

The first Source Row for a Normalized Email is an Import; every subsequent
one — including an exact duplicate — is a Merge (GLOSSARY.md: Import
Outcome, Merge).

`merge_candidate` is the single seam both call sites share:

- `deduplicate` uses it to fold rows within one Import's Source Rows.
- A later ticket (06) uses it again to fold the winning row of each group
  against a Candidate already in the database, so a re-upload counts as a
  Merge rather than an Import — `existing` there is the row read back from
  the database instead of a prior Source Row.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import Candidate


@dataclass(frozen=True)
class MergeOutcome:
    """One Normalized Email's result after folding.

    `merged_rows` counts the Source Rows folded in *beyond the first*, because
    the Import Report counts rows, not emails: an email appearing three times
    is one Import and **two** Merges. A boolean here would report one, and the
    fixture would never reveal it -- no email in it appears more than twice.
    """

    candidate: Candidate
    merged_rows: int = 0

    @property
    def is_merge(self) -> bool:
        return self.merged_rows > 0


def merge_candidate(existing: Candidate | None, incoming: Candidate) -> Candidate:
    """Fold `incoming` onto `existing` per the merge rule.

    If `existing` is None, `incoming` is returned unchanged — there is
    nothing to merge against, so this is an Import, not a Merge.

    Otherwise, `incoming`'s values win field by field, except a `None` on
    `incoming` never overwrites a non-null value on `existing`.
    """
    if existing is None:
        return incoming

    merged_fields = dict(existing)
    for field, incoming_value in incoming:
        if incoming_value is None:
            continue
        merged_fields[field] = incoming_value
    return existing.model_copy(update=merged_fields)


def deduplicate(rows: list[Candidate]) -> list[MergeOutcome]:
    """Group validated Candidates by Normalized Email, preserving Source Row
    order, and fold each group via `merge_candidate`.

    Returns one `MergeOutcome` per distinct Normalized Email, in the order
    each email first appears. The first row for an email yields
    `is_merge=False`; every subsequent row for that email — including an
    exact duplicate — yields `is_merge=True`.
    """
    order: list[str] = []
    folded: dict[str, Candidate] = {}
    merged_rows: dict[str, int] = {}

    for row in rows:
        email = row.email
        if email not in folded:
            order.append(email)
            folded[email] = row
            merged_rows[email] = 0
        else:
            folded[email] = merge_candidate(folded[email], row)
            merged_rows[email] += 1

    return [
        MergeOutcome(candidate=folded[email], merged_rows=merged_rows[email])
        for email in order
    ]
