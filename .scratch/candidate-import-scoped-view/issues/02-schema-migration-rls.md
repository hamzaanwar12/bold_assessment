# 02 — Schema, application role, and the RLS policy

Status: ready-for-agent
Type: task
Blocked by: 01
Spec: ../spec.md · ADR: ../../../docs/adr/0002-rls-for-region-scoping.md

## Goal

One Alembic revision that creates the schema, the non-owner application role, and the
Row-Level Security policy. Schema and authorization model version together because
they are inseparable.

## Scope

- Tables per spec (Schema): `candidates`, `recruiters`, `recruiter_regions`.
- `candidates.email` unique — this is the Normalized Email and the Candidate identity
  (ADR 0001). `legacy_candidate_id` deliberately **not** unique.
- Check constraints: `region_code` restricted to the six canonical Regions; `status`
  restricted to the Candidate Status enum. The database should refuse invalid values
  even if application validation were bypassed.
- Nullable: `phone`, `salary_expectation`, `applied_date`, `notes`.
- Indexes: `candidates(region_code)`, `candidates(status)`,
  `recruiter_regions(recruiter_id, region_code)`.
- Create the `techforce_app` role. Grant it DML on the three tables. It must **not**
  own them.
- `ALTER TABLE candidates ENABLE ROW LEVEL SECURITY` **and**
  `FORCE ROW LEVEL SECURITY`.
- The policy: a Candidate row is visible when the current Recruiter is an Admin, or
  when the Candidate's Region is in that Recruiter's Assigned Regions. The policy
  reads the Recruiter identifier from a session setting and **resolves the Regions
  itself** by querying `recruiter_regions` / `recruiters.is_admin`.
- `recruiters` and `recruiter_regions` must remain readable by `techforce_app`, or
  the policy's own lookup fails.

## Acceptance

- `alembic upgrade head` on an empty database succeeds; `downgrade` reverses it.
- Connected as `techforce_app` with no session setting: selecting from `candidates`
  errors or returns nothing — it must not return rows.
- The policy references no region list supplied by the caller. Only a Recruiter
  identifier crosses the boundary.

## Notes

**This is the ticket where the whole authorization model can silently fail.** RLS
does not apply to a table's owner or to a superuser. If the API later connects as the
migration role, the policy exists and protects nothing, and every API-level test
still passes. The non-owner role and `FORCE ROW LEVEL SECURITY` are two independent
guards; ticket 09 adds the third. Read ADR 0002 before changing anything here.

Decide and document how the Recruiter identifier reaches the session setting safely.
It is a session variable set from request input, so it must be parameterized like any
other value — string-interpolating it into a `SET` statement would reintroduce
injection at the exact point the security model depends on.
