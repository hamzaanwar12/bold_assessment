# 06 — POST /api/v1/candidates/import

Status: ready-for-agent
Type: task
Blocked by: 03, 05
Spec: ../spec.md (Import pipeline, API contract)

## Goal

Accept the CSV, run the four-phase pipeline, batch-write the survivors in one
transaction, and return the Import Report.

## Scope

Four phases in order:

1. **Parse** with a real CSV reader. The file is CRLF-terminated and `C-1050` has a
   quoted field containing newlines — splitting on newlines is wrong and will corrupt
   that row and everything after it. Decode UTF-8.
2. **Validate** every Source Row (ticket 04), accumulating Rejections with their
   1-based Source Row number (excluding the header) and reason. Validate everything
   before writing anything.
3. **Deduplicate in memory** (ticket 05).
4. **Write once**: a single multi-row upsert keyed on the Normalized Email unique
   index, inside one transaction. **No per-row insert in a loop** — the brief calls
   this out explicitly.

Contract:

- `multipart/form-data` file upload.
- Requires the Recruiter identifier header, **Admin only**, else `403` (inferred
  decision — see spec: API contract).
- `200` → `{imported, merged, rejected: [{row, reason}]}`.
- Non-CSV or undecodable upload → `400`.
- Row Rejections do **not** make the request fail. A database error does: `5xx`, with
  the transaction rolled back and nothing written.

## Acceptance

Importing `data/candidates_import.csv` as `R-101`:

- Returns `200` with a report whose Rejections are exactly: the three email failures,
  the impossible date, the three Region failures, and the two Status failures.
- `merged` accounts for `C-1004`, `C-1031`, and `C-1032`.
- The row numbers in the report point at the right Source Rows — verify against the
  file, since an off-by-one from the header is the easy mistake here.
- `C-1050`'s multi-line notes land intact in one Candidate.
- The same POST as `R-102` returns `403` and writes nothing.
- A forced database error leaves the table empty.

## Notes

All database access parameterized or through the ORM — some rows exist specifically
to test this, and ticket 09 asserts it.
