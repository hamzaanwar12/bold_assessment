# 2. Region scoping is enforced by PostgreSQL Row-Level Security

Date: 2026-10-26

## Status

Accepted

## Context

A Recruiter must see only Candidates in their Assigned Regions; an Admin sees all.
There are three places this could be enforced:

1. **The client** — fetch everything, filter in React. Trivially bypassable; the
   brief explicitly disqualifies it.
2. **The application** — a `WHERE region_code IN (...)` added by Python code. Correct
   as long as every present and future read path remembers to add it. The brief
   accepts this; its weakness is that the guarantee is a convention, not a property.
3. **The database** — a Row-Level Security policy on `candidates`.

Within option 3 there is a second, sharper choice: the policy can either trust a
region list the application supplies per request, or resolve the regions itself from
a Recruiter identifier.

## Decision

RLS on `candidates` is the enforcement point. Specifically:

- Each request opens a transaction and sets **only** `app.recruiter_id` via
  `SET LOCAL`.
- The policy resolves Assigned Regions itself, by looking up `recruiter_regions` and
  `recruiters.is_admin` from that identifier.
- The API connects as a dedicated **non-owner** role, `techforce_app`, and
  `candidates` carries `FORCE ROW LEVEL SECURITY`.
- A single repository function remains the only read path in application code —
  defence in depth and one place to point at in review.

## Consequences

Good:

- The guarantee is structural. A future endpoint that forgets to scope its query
  returns zero rows rather than leaking the table.
- Because the policy resolves regions from the Recruiter id, an application bug
  cannot widen a Recruiter's visibility by passing the wrong region list. The
  application is not trusted with the answer, only with the question.
- It is demonstrable outside the application entirely: `psql` as `techforce_app`
  with `app.recruiter_id` set returns the scoped rows. That is the proof that the
  control is not in the API.

Bad / accepted:

- **RLS does not apply to a table's owner or to a superuser.** This is the trap: the
  policy can exist, the tests can pass, and the protection can be entirely absent
  because the connection happens to own the table. Mitigated with two independent
  guards — the non-owner `techforce_app` role, and `FORCE ROW LEVEL SECURITY` — and
  by requiring the authorization tests to connect as `techforce_app`. Noted here
  because a future reader who switches the connection string back to the owner for
  convenience will silently disable the entire authorization model.
- The policy's subquery runs per row scanned; needs an index on
  `recruiter_regions(recruiter_id, region_code)` and on `candidates(region_code)`.
  Fine at this size, worth measuring at scale.
- Authorization logic now lives in a migration rather than in application code,
  which is a less obvious place to look for it. Hence this ADR.
- The import path writes globally and is deliberately **not** governed by the policy;
  it is gated separately by an Admin-only check in the application.
