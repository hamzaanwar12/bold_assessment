# 07 — GET /api/v1/candidates, scoped at the data layer

Status: ready-for-agent
Type: task
Blocked by: 06
Spec: ../spec.md (Authorization, API contract) · ADR: ../../../docs/adr/0002-rls-for-region-scoping.md

## Goal

A paginated, searchable, filterable Candidate list where the Region fence is enforced
by PostgreSQL, not by this endpoint.

## Scope

- Resolve the Recruiter from the identifier header in a dependency. Unknown
  identifier → **`403` before any Candidate query is constructed**. Not an empty
  `200`: that is indistinguishable from "no Candidates in your Regions" and hides a
  bad caller.
- The API connects as the **non-owner application role** from ticket 02. Verify this
  is actually the connection in use, not the migration role.
- Per request: open a transaction, `SET LOCAL` the Recruiter identifier (parameterized),
  run the query. Pass **only** the identifier — never a region list.
- One repository function is the only Candidate read path. No query construction in
  the router.
- Query parameters: `search`, `status`, `page`, `page_size` (default 25, max 100).
- Response `{items, total, page, page_size}`.
- **Compute `total` inside the scoped transaction.** Outside it, `total` leaks the
  global Candidate count while `items` looks correctly fenced — and every test
  written against `items` still passes.
- `search`: case-insensitive substring across first name, last name, email, desired
  role. No accent folding (documented scope call).
- `status`: filters on Candidate Status; combines with `search`.
- Responses are UTF-8 so Unicode names survive the wire.

## Acceptance

- As `R-103` (Marisol): only `PH-MNL` and `CO-BOG` Candidates; `total` matches that
  scoped count.
- As `R-101` (Dana, Admin): all Candidates.
- As `R-999`: `403`.
- Searching as `R-103` for a Candidate who exists only in `US-MW` returns nothing —
  search cannot escape the scope.
- `page_size=500` is clamped to 100.
- Pagination is stable across pages (deterministic ordering — add one if absent, or
  page 2 may repeat or skip rows).

## Notes

The repository function is defence in depth, not the control. If it were removed, RLS
must still fence the results. Ticket 09 proves that independently of this endpoint.
