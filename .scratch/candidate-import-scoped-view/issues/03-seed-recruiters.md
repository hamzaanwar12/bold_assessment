# 03 — Seed the Recruiter roster

Status: resolved
Type: task
Blocked by: 02
Spec: ../spec.md

## Goal

One idempotent command that loads the five Recruiters from `data/recruiters.csv`.

## Scope

- Parse `assigned_regions`: `*` sets the Admin flag; otherwise split on `|` into
  `recruiter_regions` rows.
- An Admin gets **no** `recruiter_regions` rows — their visibility does not depend on
  that table (see GLOSSARY: Assigned Regions).
- Idempotent: running it twice leaves the same state, with no duplicate region rows.
- Runs as the migration role, not the application role — seeding the roster is not a
  Candidate read and should not be subject to the policy.

## Acceptance

- After one run: 5 Recruiters; `R-101` is the Admin; `R-102` has `US-MW` and `US-NE`;
  `R-103` has `PH-MNL` and `CO-BOG`; `R-104` has `US-W` and `US-SE`; `R-105` has
  `US-NE` only.
- Running it a second time changes no row counts.

## Notes

Caleb (`R-102`) and Marisol (`R-103`) have disjoint Region sets. That is the pair the
brief names for the demonstration, so verify both load correctly — the whole scoping
demo rests on them.
