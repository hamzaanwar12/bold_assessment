# 05 — Deduplicate and merge on Normalized Email

Status: resolved
Type: task
Blocked by: 04
Spec: ../spec.md · ADR: ../../../docs/adr/0001-email-as-candidate-identity.md

## Goal

Fold the validated Source Rows so the database sees each Normalized Email at most
once per Import, and report how many were Merges.

## Scope

- Group validated rows by Normalized Email, preserving Source Row order.
- Merge rule: **last-writer-wins by Source Row order**, with one override — a null
  never overwrites a non-null.
- Count: the first row for an email is an Import; every subsequent one is a **Merge**,
  including an exact duplicate.
- A Merge against a Candidate already in the database (a re-upload) also counts as a
  Merge, not an Import.

## Acceptance

Against `data/candidates_import.csv`:

- `C-1004` appears twice → one Candidate, one Merge.
- `C-1031` and `C-1001` share a Normalized Email → one Candidate. Last-writer-wins
  means `source` becomes `Indeed` and the notes become `Possible re-application`.
- `C-1032` and `C-1016` share a Normalized Email → one Candidate, name `A. Diallo`,
  salary `110000`, applied date `2026-06-20`.
- `C-1010` is used by two rows with **different** emails → **two** Candidates, both
  carrying `C-1010` as Legacy Candidate ID.
- Re-running the same Import produces `imported: 0` and every surviving row as a
  Merge.

## Notes

The `A. Diallo` outcome is correct per the rule and is **expected to look wrong** to a
reviewer reading the table: the later Source Row carries a less complete name and
wins. Do not add a "prefer the more complete value" heuristic — it was considered and
rejected because it cannot be stated as a single rule. It is called out in NOTES.md
instead (ticket 10).
