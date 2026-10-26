# 08 — Recruiter view: table, filters, switcher

Status: resolved
Type: task
Blocked by: 07
Spec: ../spec.md (Frontend)

## Goal

A single page where flipping between Caleb and Marisol visibly changes the Candidates.

## Scope

- Candidate table: name, email, Region, desired role, Candidate Status, applied date.
- One data-fetching hook: `fetch` + `AbortController` + local state. **No data-
  fetching library** — one screen, one query.
- Text search input, debounced before firing.
- Candidate Status filter as a select.
- Recruiter switcher as a select over the five Recruiters; selecting one changes the
  Recruiter identifier header sent.
- `403` → inline error message above a **cleared** table. "Not authorized" and "no
  results" must not look the same; distinguishing them is the point of the view.
- A loading indication, so "still fetching" is distinguishable from "nothing here".
- Unicode renders correctly: `Nguyễn Thị Hoa`, `Jürgen Müller`, `Wesley Trần`.
- Minimal styling. Explicitly not graded.

## Acceptance

- Switching `R-102` → `R-103` replaces `US-MW`/`US-NE` Candidates with
  `PH-MNL`/`CO-BOG` ones.
- `R-101` shows Candidates from every Region.
- Typing in search issues one request after the debounce, not one per keystroke.
- Status filter narrows the table and combines with search.
- An unknown Recruiter identifier (set by hand) shows the error banner, not an empty
  table.
- Accented and non-Latin names are not mangled.

## Notes

`AbortController` is not optional polish. Without it, switching Recruiter while a
request is in flight can let the older response land last and render the **previous**
Recruiter's Candidates — which looks exactly like an authorization bug during a
demonstration, and is the single most embarrassing failure mode for this screen.
