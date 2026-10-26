# 04 — Normalization and the rejection boundary

Status: ready-for-agent
Type: task
Blocked by: 01
Spec: ../spec.md (Normalization and the rejection boundary)

## Goal

Turn a raw Source Row into either a valid Candidate or a Rejection carrying a
human-readable reason. Pydantic v2 defines what a valid Candidate is.

## Scope

Normalizers as pure functions, one per field family: email, Region, Candidate Status,
applied date, salary. Each returns a normalized value or signals a Rejection reason.

Rules — implement exactly as specified, including the asymmetries:

| Field | Normalize | Reject when |
|---|---|---|
| Email | trim, lowercase | malformed or empty |
| Region | trim, uppercase | not one of the six canonical codes, or empty |
| Status | case-fold | not in the canonical enum |
| Applied date | accept `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY` | no real calendar date; **empty → unknown, not rejected** |
| Salary | strip `$`, commas, whitespace; expand `k`/`K` | never — non-numeric or empty → unknown |
| Phone | trim | never |
| Names / role / source / notes | trim | never — store verbatim |

Three rules are counter-intuitive and must not be "improved":

- **`USW` is rejected, not repaired to `US-W`.** A one-character inference on the
  authorization axis is out of bounds.
- **An empty Region is rejected**, even though the row is otherwise fine. A
  Region-less Candidate is invisible to every scoped Recruiter and owned by nobody.
- **`actve` and `on hold` are rejected.** No fuzzy matching, no catch-all enum
  member. Guessing a Candidate Status invents business meaning.

Rejection reasons are written for a human reading the Import Report, naming the field
and the offending value.

## Acceptance

Verifiable against the fixture once ticket 06 wires it up, but the rules to satisfy:

- `us-mw` → `US-MW`; `" CO-BOG "` → `CO-BOG`; `USW`, `ZZ-99`, empty → rejected.
- `ACTIVE` → `active`; `actve`, `on hold` → rejected.
- `06/30/2026` and `14-May-2026` parse; `2026-02-30` rejected; empty → unknown.
- `"$95,000"` → `95000`; `"97,500"` → `97500`; `85k` → `85000`; `negotiable` and
  empty → unknown.
- `"  Alicia.Trent@Gmail.com "` → `alicia.trent@gmail.com`; `marcus.reed[at]gmail.com`
  and `tina.holloway.gmail.com` and empty → rejected.
- Text fields preserve Unicode exactly: `Nguyễn Thị Hoa`, `Jürgen Müller`,
  `Wesley Trần`, `Sofía`, `Tomás`, `Lucía`.

## Notes

These functions are **not** a test seam (see spec: Testing Decisions). Every outcome
above is observable in the Import Report, so they are exercised through the HTTP seam
in ticket 09. Resist adding a unit-test file here; it would assert internal structure
and need rewriting the moment normalization moves.
