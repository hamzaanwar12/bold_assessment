# 09 — Test suite

Status: ready-for-agent
Type: task
Blocked by: 08
Spec: ../spec.md (Testing Decisions)

## Goal

Tests that assert externally observable behaviour across three justified seams, and
that prove the authorization claim rather than assuming it.

## Scope

**Environment.** Separate test database in the same container, migrated once per
session, each test in a transaction rolled back at teardown — the suite must be safe
to run mid-demonstration without destroying the data on screen.

**Seam 1 — HTTP boundary** (in-process client, real PostgreSQL):

1. Exact duplicate `C-1004` collapses to one Candidate, counted as `merged`.
2. `C-1031` merges into `C-1001`: one Candidate, last-writer-wins field values.
3. `C-1010` collision yields **two** Candidates.
4. Invalid and missing emails rejected, each with Source Row number and reason.
5. `2026-02-30` rejected; empty applied date imported as unknown.
6. `USW`, `ZZ-99`, and empty Regions rejected.
7. Injection rows: import succeeds, payloads stored as **literal text**, and the
   `candidates` table **still exists** afterwards.
8. Import as a non-Admin → `403`, nothing written.
9. Unknown Recruiter identifier on the read endpoint → `403`, not empty `200`.
10. Pagination: default size, `page_size` clamped at 100, `total` equals the scoped
    count.
11. Search matches name / email / desired role case-insensitively and combines with
    the Status filter.

**Seam 2 — direct database connection as the application role:**

12. Set the Recruiter identifier to `R-103`, run a bare `SELECT` on `candidates`:
    only `PH-MNL` / `CO-BOG` rows. Set it to `R-101`: all rows.

**Seam 3 — rendered component (Vitest + RTL):**

13. Changing the Recruiter switcher changes the Recruiter identifier sent on the
    request.

## Acceptance

- Backend suite green in one command; frontend suite green in one command. Both run
  on camera.
- Test 7 asserts table existence, not just the stored string. A string-only assertion
  passes even if a second statement executed.
- Test 12 connects as the **application role**. If the fixture hands it the migration
  connection, the test passes while verifying nothing — this is the specific failure
  ADR 0002 exists to prevent, and it is the one test in the suite that is worthless if
  mis-wired. Verify the role in use inside the test.

## Notes

**Do not add unit tests for the normalizers.** Their behaviour is covered by tests
4–6 through the Import Report. A fourth seam asserting internal structure is a cost,
not coverage (see spec: Testing Decisions).
