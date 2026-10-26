# Spec: Candidate Import & Scoped Recruiter View

Status: resolved
Feature: candidate-import-scoped-view

## Problem Statement

TechForce's recruiting operations run on candidate data that arrives as exports from
whatever system held it before — in this case a legacy CSV that is actively hostile:
the same person appears three times under three different identifiers, one identifier
is reused for two different people, emails arrive with stray capitalisation and
surrounding whitespace or with no `@` at all, dates arrive in three formats plus one
that does not exist (`2026-02-30`), salaries arrive as `"$95,000"` and `85k` and
`negotiable`, Regions arrive as `us-mw` and `USW` and `ZZ-99`, and two rows contain
SQL injection payloads sitting in ordinary text fields.

Loading that file naively produces a database nobody can trust: duplicate people
inflating pipeline counts, silently dropped rows nobody knows are missing, and
free-text columns that have been interpreted rather than stored.

Separately, Recruiters are accountable for specific Regions. Caleb covers `US-MW` and
`US-NE`; Marisol covers `PH-MNL` and `CO-BOG`. A Recruiter seeing outside their
Assigned Regions is not a cosmetic problem — it is an authorization failure. And an
authorization control implemented as a filter in the React table, or as a `WHERE`
clause one endpoint remembers to add, is a control that stops working the first time
someone adds a second endpoint.

## Solution

Three pieces, all thin:

1. **An Import endpoint** that accepts the CSV, validates every Source Row against an
   explicit definition of a valid Candidate, normalizes what can be normalized,
   deduplicates against Normalized Email, writes the survivors in one batch, and
   returns an **Import Report** — `{imported, merged, rejected: [{row, reason}]}`.
   Nothing is silently dropped: every rejected Source Row comes back with its row
   number and why.

2. **A scoped read endpoint** where the region fence lives in PostgreSQL itself, as a
   Row-Level Security policy that resolves a Recruiter's Assigned Regions from the
   database rather than from anything the request supplies. The application is
   trusted to say *who is asking*, never *what they may see*.

3. **A single-page Recruiter view** — a Candidate table with text search, a Candidate
   Status filter, and a Recruiter switcher, so the scoping can be demonstrated by
   flipping from Caleb to Marisol and watching the rows change.

The deduplication, normalization, and rejection rules are all explicit and uniformly
applied. Where the source data is genuinely ambiguous, the rule is written down and
its cost acknowledged, rather than being resolved case by case.

## User Stories

**Import**

1. As a recruiting operations lead, I want to upload a candidate CSV through an API endpoint, so that I can load a legacy export without hand-editing it first.
2. As a recruiting operations lead, I want an Import Report telling me how many Candidates were created, so that I can confirm the load did what I expected.
3. As a recruiting operations lead, I want every rejected Source Row reported with its row number, so that I can go back to the source file and fix it.
4. As a recruiting operations lead, I want every rejected Source Row reported with a human-readable reason, so that I know whether it is a data problem or a rule I should reconsider.
5. As a recruiting operations lead, I want rows counted as `merged` separately from `imported`, so that I can tell "40 new people" apart from "40 new rows about 30 people".
6. As a recruiting operations lead, I want rows that fail validation to be rejected rather than silently skipped, so that my Candidate count can never quietly disagree with my source file.
7. As a recruiting operations lead, I want valid rows to load even when some rows are rejected, so that one bad row in a thousand does not block the whole import.
8. As a recruiting operations lead, I want a database failure mid-import to leave the database exactly as it was, so that I never have to work out how far a half-finished import got.
9. As a recruiting operations lead, I want re-uploading the same file to be safe, so that I can retry an import without creating a second copy of everyone.
10. As a platform engineer, I want the import to write in batches rather than one row at a time, so that loading a large export does not take minutes of round-trips.

**Identity and deduplication**

11. As a recruiting operations lead, I want one person who appears several times in the export to end up as one Candidate, so that my pipeline counts are not inflated.
12. As a recruiting operations lead, I want email matching to ignore capitalisation and surrounding whitespace, so that `"  Alicia.Trent@Gmail.com "` and `alicia.trent@gmail.com` are recognised as the same person.
13. As a recruiting operations lead, I want an exact duplicate row to be recognised and counted as a Merge, so that it shows up in the report rather than passing unnoticed.
14. As a recruiting operations lead, I want two different people who happen to share a Legacy Candidate ID to remain two Candidates, so that a flaw in the source system's keys does not destroy a real person's record.
15. As a recruiting operations lead, I want the Legacy Candidate ID kept on each Candidate, so that I can trace any record back to the source export.
16. As a recruiting operations lead, I want the merge rule to be one stated rule applied everywhere, so that I can predict the outcome without inspecting the data.
17. As a recruiting operations lead, I want a Merge never to replace a value I have with a blank, so that a sparse later row cannot erase details from an earlier one.

**Normalization**

18. As a recruiter, I want Region codes accepted regardless of case or padding, so that `us-mw` and `" CO-BOG "` load instead of failing.
19. As a recruiting operations lead, I want Region codes that cannot be confidently resolved to be rejected rather than guessed, so that nobody is assigned to a Region based on a one-character inference.
20. As a recruiting operations lead, I want a Candidate with no Region to be rejected, so that I never hold a Candidate who is invisible to every Recruiter and owned by nobody.
21. As a recruiter, I want Candidate Status accepted regardless of case, so that `ACTIVE` loads as `active`.
22. As a recruiting operations lead, I want an unrecognised Candidate Status to be rejected rather than guessed, so that nobody's pipeline position is invented from a typo.
23. As a recruiter, I want applied dates accepted in the formats the export actually uses, so that US-formatted and text-formatted dates both load.
24. As a recruiting operations lead, I want a missing applied date to load as unknown, so that I do not lose a real Candidate over a blank cell.
25. As a recruiting operations lead, I want an impossible calendar date to be rejected, so that a corrupt value is reported rather than quietly coerced into a different day.
26. As a recruiter, I want salary figures stripped of currency symbols and thousands separators, so that they are stored as numbers I can sort and compare.
27. As a recruiter, I want a `k`-suffixed salary expanded to its full value, so that `85k` sorts next to `86000` instead of lexically.
28. As a recruiter, I want a non-numeric salary like `negotiable` stored as unknown rather than rejecting the Candidate, so that I keep a good Candidate whose salary is genuinely open.
29. As a recruiter, I want a Candidate with no phone number to still load, so that a missing optional field does not cost me a Candidate.

**Security**

30. As a platform engineer, I want SQL injection payloads in text fields stored as literal text, so that hostile source data cannot execute anything.
31. As a platform engineer, I want every database access parameterized or ORM-mediated, so that injection is impossible by construction rather than by review diligence.
32. As a security reviewer, I want to confirm the `candidates` table still exists after importing a row containing `DROP TABLE candidates`, so that I have direct evidence the payload was inert.
33. As a security reviewer, I want region scoping enforced inside PostgreSQL, so that the control does not depend on the application remembering to apply it.
34. As a security reviewer, I want the scoping policy to resolve a Recruiter's Assigned Regions from the database itself, so that an application bug cannot widen someone's visibility by passing the wrong list.
35. As a security reviewer, I want the API to connect as a role that does not own the tables, so that Row-Level Security actually applies to it instead of being bypassed.
36. As a security reviewer, I want to reproduce the scoping in a `psql` session, so that I can see the guarantee holds with the API out of the picture entirely.
37. As a security reviewer, I want an unknown Recruiter identifier to be refused outright, so that an invalid caller gets an error rather than a successful empty response that looks like "no candidates".
38. As a recruiting operations lead, I want the Import endpoint restricted to Admins, so that a Region-scoped Recruiter cannot write Candidate data outside their remit.

**Scoped reading**

39. As Caleb, I want to see only Candidates in `US-MW` and `US-NE`, so that I work on the Candidates I am accountable for.
40. As Marisol, I want to see only Candidates in `PH-MNL` and `CO-BOG`, so that I am not distracted by Candidates I cannot act on.
41. As Dana, an Admin, I want to see Candidates in every Region, so that I can oversee the whole pipeline.
42. As a recruiter, I want the total count alongside my results to reflect only what I am allowed to see, so that the count does not reveal how many Candidates exist outside my Regions.
43. As a recruiter, I want results paginated, so that the response stays fast as the Candidate list grows.
44. As a recruiter, I want a sane default page size and an enforced maximum, so that a careless request cannot pull the entire table.
45. As a recruiter, I want to search Candidates by name, so that I can find a specific person I am expecting a call from.
46. As a recruiter, I want to search by email and desired role as well as name, so that one box covers the ways I actually remember a Candidate.
47. As a recruiter, I want search to be case-insensitive, so that I do not have to match capitalisation.
48. As a recruiter, I want to filter by Candidate Status, so that I can work through everyone at `screening` in one pass.
49. As a recruiter, I want search and the Status filter to combine, so that I can narrow to one Candidate at one stage.
50. As a recruiter, I want search and filtering to respect my Region scope, so that searching can never surface a Candidate I am not allowed to see.

**Recruiter view**

51. As a recruiter, I want a single table of Candidates showing name, email, Region, desired role, Candidate Status, and applied date, so that I can scan my pipeline at a glance.
52. As a recruiter, I want a search box above the table, so that I can narrow the list without constructing a URL.
53. As a recruiter, I want search to wait briefly before firing, so that typing does not issue a request per keystroke.
54. As a recruiter, I want a Candidate Status dropdown, so that I can filter without typing.
55. As a reviewer, I want a Recruiter switcher listing the five Recruiters, so that I can flip between Caleb and Marisol and watch the visible Candidates change.
56. As a reviewer, I want switching Recruiter to change the identifier the browser actually sends, so that I am observing real server-side scoping rather than a client-side filter.
57. As a recruiter, I want names with accents and non-Latin characters rendered correctly, so that `Nguyễn Thị Hoa` and `Jürgen Müller` appear as their actual names.
58. As a recruiter, I want a clear message when my request is refused, so that I am not left looking at an empty table wondering whether I have no Candidates or no access.
59. As a recruiter, I want an in-flight request cancelled when I switch Recruiter, so that a slow earlier response cannot arrive late and show me the previous Recruiter's Candidates.
60. As a recruiter, I want to see that the table is loading, so that I can tell "still fetching" apart from "nothing here".

**Operability**

61. As a new engineer, I want setup steps that work on a clean machine, so that I can run the project without reverse-engineering anyone's local environment.
62. As a new engineer, I want the database startable with one command, so that I do not have to install and configure PostgreSQL by hand.
63. As a new engineer, I want the schema applied by a migration, so that I can recreate the database from scratch deterministically.
64. As a new engineer, I want the Recruiter roster loadable by one idempotent command, so that I can reset to a known state and run it twice safely.
65. As a new engineer, I want the deduplication and normalization rules written down, so that I can understand why a given row was rejected without reading the validator.
66. As a reviewer, I want the test suite runnable in one command and passing, so that I can verify the behaviour rather than take it on trust.
67. As a reviewer, I want the tests to use their own database, so that running them does not destroy the data I was just looking at.
68. As a reviewer, I want commit history that follows the build, so that I can read the work in the order it happened.

## Implementation Decisions

### Domain vocabulary

Terms used throughout follow `GLOSSARY.md`: **Candidate**, **Normalized Email**,
**Legacy Candidate ID**, **Region**, **Recruiter**, **Admin**, **Assigned Regions**,
**Candidate Status**, **Import Outcome**, **Source Row**, **Import Report**,
**Merge**, **Rejection**.

Two distinctions matter and are easy to blur:

- **Candidate Status** (`active`/`screening`/`interviewing`/`withdrawn`) describes a
  person. **Import Outcome** (`imported`/`merged`/`rejected`) describes a Source Row.
  Neither is called "status" unqualified anywhere in the code.
- A Candidate has one **Region**; a Recruiter has a *set* of **Assigned Regions**.
  Scoping is set membership, never equality.

### Identity and deduplication

Governed by **ADR 0001**.

- **Normalized Email** is the Candidate identity, with a unique constraint.
- `candidate_id` becomes **Legacy Candidate ID**: a plain, non-unique column.
- Consequence: the `C-1010` collision yields **two** Candidates; the
  `C-1031`/`C-1001` and `C-1032`/`C-1016` pairs are **Merges**.
- Merge rule: **last-writer-wins by Source Row order**, with one override — a null
  never overwrites a non-null.
- An exact duplicate Source Row counts toward `merged`, not `imported`.
- Accepted, documented consequence: `C-1016`'s name becomes `A. Diallo`, because the
  later Source Row wins. The alternative — preferring the "more complete" value per
  field — produces nicer output but cannot be stated as one rule, so it is rejected
  in favour of predictability.

### Normalization and the rejection boundary

The single question behind every rule: *is this value absent, or is it wrong?*
Absent values that are not identity-bearing load as unknown. Wrong values are
rejected and reported.

| Field | Normalization | Rejected when |
|---|---|---|
| Email | trim, lowercase | malformed or empty — it is the identity |
| Region | trim, uppercase | not resolvable to one of the six canonical codes, or empty |
| Candidate Status | case-fold | not in the canonical enum |
| Applied date | accept `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY` | parses to no real calendar date; **empty loads as unknown** |
| Salary | strip `$`, commas, whitespace; expand `k`/`K` suffix | never — non-numeric or empty loads as unknown |
| Phone | trim | never — optional |
| Names, role, source, notes | trim | never — stored verbatim as text |

Three judgement calls, stated deliberately:

- **An un-resolvable Region is a Rejection, not a null Region.** Region is the
  authorization axis. A Candidate with no Region is invisible to all four
  Region-scoped Recruiters and owned by nobody — a silent orphan that looks like
  successful import. `USW` is *not* repaired to `US-W`: a one-character inference on
  a security-relevant field is exactly the kind of helpful guess that becomes a
  defect later.
- **An unrecognised Candidate Status is a Rejection.** No fuzzy matching. Status
  drives Recruiter behaviour, so inferring it from a typo invents business meaning.
  `on hold` may well be a real status in the source system — which is precisely why
  it should be reported to a human rather than mapped by guesswork.
- **A missing date loads; an impossible date is rejected.** Asymmetric on purpose.
  A blank cell asserts nothing. `2026-02-30` asserts something false, and coercing
  it to March 1st or February 28th would fabricate a fact.

### Import pipeline

Four phases, in order, inside one request:

1. **Parse.** Standard CSV reader. The file is CRLF-terminated and contains a quoted
   field with embedded newlines, so splitting on newlines is incorrect — the parser
   must handle quoting. Decoded as UTF-8.
2. **Validate.** Every Source Row is validated independently; failures accumulate
   into the Rejection list with their 1-based Source Row number and reason. All rows
   are validated before anything is written.
3. **Deduplicate in memory.** Valid rows are folded on Normalized Email, applying the
   merge rule. The database sees each Normalized Email at most once per Import.
4. **Write in one batch, in one transaction.** A single multi-row upsert keyed on the
   Normalized Email unique index. No per-row insert in a loop. Any database failure
   rolls back the entire Import.

Rejections do not abort the Import: the response is `200` with the Import Report.
A rejected row is a fact about the data, not a failed request. A *database* failure
is a failed request and surfaces as a `5xx` with nothing written.

### API contract

**`POST /api/v1/candidates/import`**

- `multipart/form-data` file upload.
- Requires a Recruiter identifier header; **Admin only**, otherwise `403`. The brief
  does not specify this, so it is an inferred decision: Region-scoped Recruiters
  should not write global Candidate data. Recorded in the write-up.
- `200` → `{imported: n, merged: n, rejected: [{row: n, reason: "..."}]}`.
- Non-CSV or undecodable upload → `400`.

**`GET /api/v1/candidates`**

- Query: `search`, `status`, `page`, `page_size`.
- Requires a Recruiter identifier header. Unknown identifier → **`403`, before any
  Candidate query runs** — never an empty `200`, which would be indistinguishable
  from "no Candidates in your Regions".
- `page_size` defaults to 25, hard maximum 100.
- `200` → `{items: [...], total: n, page: n, page_size: n}`.
- **`total` is computed inside the scoped context.** Computing it outside leaks the
  global Candidate count even while `items` is correctly fenced — a quiet
  information disclosure that passes every test written against `items`.
- `search` matches case-insensitively across first name, last name, email, and
  desired role. Accent folding is **not** implemented: verified, `muller` does not
  match `Müller`. Deliberate scope call, documented as future work. Note the gap is
  narrower than it looks -- `sofia` *does* find `Sofía Cárdenas`, because `search`
  also covers the email column and hers is `sofia.cardenas@hotmail.com`. It bites
  only where the email offers no ASCII echo of the accented name.
- `status` filters on Candidate Status.

### Schema

- `candidates` — surrogate primary key; `email` unique (the Normalized Email);
  `legacy_candidate_id` non-unique; first/last name; phone nullable; `region_code`
  not null, constrained to the six canonical Regions; desired role; `salary_
  expectation` numeric nullable; `applied_date` nullable; `status` constrained to the
  Candidate Status enum; source; notes; timestamps.
- `recruiters` — `recruiter_id` primary key; full name; email; `is_admin` boolean.
- `recruiter_regions` — `(recruiter_id, region_code)` composite key. Normalized
  rather than an array column, so the RLS policy's lookup is a plain indexed join.
- Indexes: `candidates(region_code)` (the scoping predicate),
  `recruiter_regions(recruiter_id, region_code)` (the policy lookup),
  `candidates(status)` (the filter).
- Delivered as one Alembic revision, which also creates the application role and the
  RLS policy — the schema and its authorization model are inseparable and version
  together.

### Authorization

Governed by **ADR 0002**.

- RLS policy on `candidates`. Each request opens a transaction and sets **only**
  `app.recruiter_id` with `SET LOCAL`. The policy resolves Assigned Regions itself
  from `recruiter_regions` and `recruiters.is_admin`.
- The application is trusted to say *who is asking*, never *what they may see*. Had
  the application passed the region list, a buggy endpoint could pass the wrong one
  and the database would faithfully honour it.
- **The API connects as a dedicated non-owner role, and `candidates` carries
  `FORCE ROW LEVEL SECURITY`.** This is the decision most likely to be undone by
  accident: RLS does not apply to a table's owner or to a superuser, so running the
  API on the migration connection makes the policy exist while protecting nothing —
  and every test written against the API still passes. Two independent guards, plus
  an authorization test that connects as the application role specifically.
- One repository function is the only Candidate read path in application code.
  Defence in depth, and a single place to point at during review.
- Recruiter resolution (and the `403` for an unknown identifier) happens in a
  dependency, before any Candidate query is constructed.

### Frontend

- Vite + React + TypeScript. One page, one table.
- A single data-fetching hook using `fetch` with an `AbortController`. No data-
  fetching library: one screen with one query gains nothing from a cache, and the
  only real race — an in-flight request outliving a Recruiter switch — is exactly
  what `AbortController` solves. Without it, a slow earlier response can land after
  a newer one and display the previous Recruiter's Candidates, which would look
  exactly like an authorization bug.
- Vite dev-server proxy to the API. No CORS middleware, and therefore no permissive
  `allow_origins` configuration living in the repository.
- Search input debounced before issuing a request.
- Recruiter switcher is a plain select over the five Recruiters; selecting one
  changes the Recruiter identifier header the browser sends.
- `403` renders an inline error message above a cleared table. Distinguishing "not
  authorized" from "no results" is the whole point; an empty table for both would
  hide the control being demonstrated.
- Styling is minimal and explicitly not part of the deliverable.

### Operational setup

- `docker-compose.yml` provides PostgreSQL only. Application services are run on the
  host. Containerising the API and frontend adds build time without changing what is
  being evaluated; only the database needs to be reproducible.
- One idempotent seed command loads the five Recruiters, parsing `*` into the Admin
  flag and the pipe-delimited list into `recruiter_regions` rows. Re-runnable.
- No Recruiter management endpoints; the roster is fixture data.

## Testing Decisions

### What makes a good test here

Tests assert **externally observable behaviour**: what the API returns, what the
database contains afterwards, what the rendered UI sends. They do not assert that a
particular function was called, that normalization happens in a specific module, or
that the pipeline has four phases. Every rule in this spec is observable from
outside — a Rejection appears in the Import Report, a Merge appears as a changed
Candidate count, scoping appears as rows present or absent — so there is no rule
that requires reaching inside to verify.

### Seams

Three seams, which is more than the ideal of one. Each additional seam earns its
place:

1. **The HTTP boundary (primary).** An in-process test client against the FastAPI
   app, backed by a real PostgreSQL. Every import rule, every normalization rule,
   every pagination and search behaviour, and the `403` paths are tested here. This
   is the highest available seam and carries the large majority of the suite.

2. **A direct database connection as the application role.** Required, not
   preferred. The claim under test is *"the region fence is in the database, not in
   the application"*, and that claim is unfalsifiable from the HTTP seam — a test
   through the API passes identically whether the filter came from RLS or from a
   Python `WHERE` clause. Proving it needs a connection with the API out of the
   picture: set the Recruiter identifier, run a bare `SELECT`, observe scoped rows.
   This seam also catches the owner-bypass trap, which is invisible from above.

3. **The rendered component.** One test on the Recruiter switcher, asserting that
   selecting a different Recruiter changes the identifier sent on the request. The
   brief only requires pytest; this is a deliberate addition, because "the switcher
   changes the header" is the one frontend behaviour that the entire scoping
   demonstration rests on, and it cannot be observed from the backend seam.

**Deliberately not a seam: the normalization functions.** They are pure and would be
pleasant to unit test, but every one of their outcomes is already visible in the
Import Report — a bad Region appears as a Rejection with a reason, `85k` appears as a
stored numeric. Testing them separately would add a fourth seam that asserts internal
structure and would need rewriting if normalization moves. If a specific rule turns
out hard to pin down through the Import Report, that is the signal to add the seam,
not before.

### Coverage

Through the HTTP seam:

- An exact duplicate Source Row collapses to one Candidate and is counted as
  `merged`.
- A case-and-whitespace email variant Merges into the existing Candidate; one
  Candidate results, and the surviving field values follow last-writer-wins.
- Two Source Rows sharing a Legacy Candidate ID with different emails produce **two**
  Candidates.
- Malformed and missing emails are rejected, each with its Source Row number and a
  reason.
- An impossible date is rejected; a missing date loads with an unknown applied date.
- Un-resolvable and empty Regions are rejected.
- Rows containing SQL injection payloads import, the payloads are stored as literal
  text, and the `candidates` table still exists afterwards. The table-existence
  assertion matters: a test that only checks the stored string would pass even if a
  second statement had executed.
- Pagination honours its default and its maximum; `total` reflects the scoped count.
- Search matches across the intended fields, case-insensitively, and combines with
  the Status filter.
- The Import endpoint returns `403` for a non-Admin Recruiter.
- An unknown Recruiter identifier returns `403`, not an empty `200`.

Through the database seam:

- A Region-scoped Recruiter cannot retrieve a Candidate outside their Assigned
  Regions, and an Admin can — asserted while connected as the application role.

Through the component seam:

- Changing the Recruiter switcher changes the Recruiter identifier sent.

### Test environment

A separate test database in the same containerised PostgreSQL, migrated once per
session, with each test wrapped in a transaction rolled back at teardown. Two
reasons: the suite must be safe to run at any moment without destroying the data
being demonstrated, and rollback-per-test is faster than re-seeding.

The authorization tests must connect as the application role. A fixture that hands
them the migration connection would make them pass while testing nothing, which is
the specific failure ADR 0002 exists to prevent.

### Prior art

None — this is a new codebase. The patterns established here are the prior art for
what follows, which is why the seams are written down rather than left implicit.

## Out of Scope

- Any login or session flow, JWT, or password handling. Caller identity is a header,
  as the brief specifies.
- Candidate write operations other than Import: no create, update, or delete
  endpoints.
- Recruiter management. The roster is seeded fixture data.
- Accent-insensitive search. Verified: `muller` will not match `Müller`. Noted as
  future work.
- A CSS framework or design system. Styling is minimal by instruction.
- Containerising the API or frontend. Only PostgreSQL is containerised.
- A CI pipeline.
- Audit logging, soft deletes, and Candidate history.
- Background or asynchronous import. The Import is synchronous; the dataset is small
  enough that a job queue would be unjustified complexity.
- Identity-merge workflow for a Candidate who changes email. See ADR 0001.

## Further Notes

**The highest-risk decision is also the quietest.** Row-Level Security does not apply
to a table's owner or to a superuser. If the API's connection is ever pointed at the
migration role — a one-line change that looks like a convenience — the policy will
still exist, the API will still return scoped results in every test written against
it, and the authorization model will be entirely absent. The non-owner role, `FORCE
ROW LEVEL SECURITY`, and an authorization test bound to the application role are
three independent defences against one mistake. Anyone touching the connection
configuration should read ADR 0002 first.

**The second quietest is the paginated total.** `items` can be perfectly fenced while
`total` reveals the global Candidate count, because the count query is easy to write
outside the scoped context. It must be computed inside it.

**Where ambiguity was resolved by inference**, the brief invites a reasonable call,
documented. Three were made: the Import endpoint is Admin-only; a missing applied
date loads while an impossible one is rejected; and an unrecognised Candidate Status
is rejected rather than mapped to a catch-all. Each is recorded in the write-up with
its reasoning, because the reasoning is the part being evaluated.

**On the merge rule's visible cost.** Last-writer-wins means a Candidate's name can
regress to a less complete form when a later Source Row carries an abbreviation. This
looks like a defect to anyone reading the output table without reading the rule. It
is called out in the write-up explicitly, in preference to a per-field "prefer the
better value" heuristic that would produce nicer output and no statable rule.
