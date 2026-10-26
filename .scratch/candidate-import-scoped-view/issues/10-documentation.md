# 10 — README, NOTES, and final docs pass

Status: resolved
Type: task
Blocked by: 09
Spec: ../spec.md

## Goal

The two documents the submission is actually graded on, plus a final check that the
domain docs match what was built.

## Scope

**`README.md`** — setup from a clean machine, verified by following it on a clean
checkout, not from memory: prerequisites, `docker compose up`, migrations, seed, run
the API, run the frontend, run both test suites, and how to perform the Import.

**`NOTES.md`** — half a page to a page:

- Dedup and merge rules, and the normalization decisions, with the reasoning. Include
  the `A. Diallo` consequence explicitly: it looks like data loss and is the rule
  working as stated.
- The three inferred calls: Import is Admin-only; a missing applied date loads while
  an impossible one is rejected; an unrecognised Candidate Status is rejected rather
  than mapped to a catch-all.
- **AI usage log**: what was delegated, what was deliberately not, and at least one
  concrete thing an AI tool produced that was caught and corrected.
- What would come next with more time: accent-insensitive search, identity-merge
  workflow for a Candidate who changes email, audit logging, CI.

**Final docs check** — confirm `GLOSSARY.md` and both ADRs still describe what was
built; update them if an implementation decision diverged.

## Acceptance

- A clean clone, following `README.md` only, reaches a running app with data loaded.
- `NOTES.md` contains a real, specific caught-and-corrected AI error — named,
  with what was wrong and what it was changed to.
- No stale claim in `GLOSSARY.md` or the ADRs.

## Notes

**The AI usage log cannot be reconstructed at the end.** Append to `NOTES.md` the
moment a correction happens, from ticket 01 onward — this ticket is the final pass,
not the first time the file is opened. An invented example here would be the single
worst thing to be caught doing in a recorded exercise.

Two likely candidates, worth watching for: filtering Regions in Python after the
fetch (explicitly disqualified by the brief), and connecting the API as the table
owner, which silently disables RLS. Log whatever actually happens.
