# NOTES

> **Living document.** Written as the work happens, not reconstructed at the end.
> The AI usage log below is appended to at the moment each event occurs.

## Dedup & merge rules

**Normalized Email (trimmed, lowercased) is the Candidate identity**, with a unique
constraint. `candidate_id` is kept as `legacy_candidate_id` — a non-unique column for
traceability only. Reasoning in [ADR 0001](docs/adr/0001-email-as-candidate-identity.md);
the short version is that the source data reuses `C-1010` for two demonstrably
different people, so it cannot be an identity, while one person appears under three
different `candidate_id` values.

Consequences on the supplied file:

| Case | Outcome |
|---|---|
| `C-1004` repeated byte-identical | one Candidate, counted as a Merge |
| `C-1031` vs `C-1001` (`"  Alicia.Trent@Gmail.com "`) | one Candidate |
| `C-1032` vs `C-1016` (`amara.diallo@gmail.com`) | one Candidate |
| `C-1010` used by two different people | **two** Candidates, both keeping `C-1010` |

**Merge rule: last-writer-wins by Source Row order**, with one override — a null never
overwrites a non-null. One sentence, applied everywhere, trivially testable.

Its visible cost, called out because it looks like a defect: `C-1016`'s name becomes
**`A. Diallo`**, not `Amara Diallo`, because the later row wins. The alternative — a
per-field "prefer the more complete value" heuristic — gives nicer output and cannot
be stated as a single rule, so I rejected it. Predictable beats clever when someone
else has to explain the result to a recruiter.

**Counting**: `imported + merged + len(rejected)` always equals the number of Source
Rows (53 here: 41 + 3 + 9). Every row has exactly one outcome. See Correction 10 —
an earlier version lost three rows and every test still passed.

## Normalization decisions

One question behind every rule: **is this value absent, or is it wrong?** Absent and
not identity-bearing → loads as unknown. Wrong → rejected and reported, never
silently dropped.

| Field | Normalization | Rejected when |
|---|---|---|
| Email | trim, lowercase | malformed or empty — it is the identity |
| Region | trim, uppercase | not one of the six canonical codes, or empty |
| Status | case-fold | not in `active/screening/interviewing/withdrawn` |
| Applied date | `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY` | not a real calendar date. **Empty loads as unknown** |
| Salary | strip `$`/commas, expand `k` | never — non-numeric or empty loads as unknown |
| Names, phone, role, source, notes | trim | never — stored as literal text |

Three calls that are deliberate and look harsh:

- **`USW` is rejected, not repaired to `US-W`.** Region is the authorization axis. A
  one-character guess there is how someone ends up in the wrong recruiter's queue.
- **An empty Region is rejected** even when the rest of the row is perfect, because a
  Region-less Candidate is invisible to all four scoped recruiters and owned by
  nobody — an import that looks successful and produces an orphan.
- **`actve` and `on hold` are rejected, with no catch-all enum member.** Status drives
  recruiter behaviour. `on hold` is probably a real status upstream, which is exactly
  why a human should see it rather than have it guessed.

And one asymmetry worth stating plainly: **a missing applied date loads; `2026-02-30`
is rejected.** A blank cell asserts nothing. An impossible date asserts something
false, and coercing it to Feb 28 or Mar 1 would fabricate a fact nobody could later
detect.

## Inferred calls (brief was ambiguous)

1. **Import is Admin-only.** The brief specifies the `X-Recruiter-Id` header for
   reads but says nothing about who may import. Region-scoped recruiters writing
   global candidate data is inconsistent with region-fenced reads, so import
   requires `is_admin` and returns 403 otherwise.
2. **A missing applied date loads; an impossible one is rejected.** Asymmetric on
   purpose: a blank cell asserts nothing, so it becomes NULL. `2026-02-30` asserts
   something false, and coercing it to Feb 28 or Mar 1 would fabricate a fact.
3. **An unrecognised status is rejected, not mapped to a catch-all.** `actve` and
   `on hold` are reported rather than guessed. Status drives recruiter behaviour,
   so inferring it from a typo invents business meaning. `on hold` may well be a
   real status upstream — which is exactly why a human should see it.

## AI usage log

**Setup / orchestration model.** Opus as orchestrator (architecture, spec, ticket
graph, diff review, merges); Sonnet workers as implementers, one per ticket, each in
its own git worktree, driven TDD-first. Guardrails in `.claude/settings.json`:
destructive operations (`push --force`, `reset --hard`, `branch -D`, `rm -rf`,
`docker compose down -v`) are denied outright rather than prompted.

### Caught and corrected


#### Correction 1 — environment audit before delegating

Before spawning any implementer, an audit of the actual environment surfaced four
problems that would each have failed silently or late:

- `git user.name` / `user.email` were unset at every scope, so the first commit any
  background agent attempted would have failed with no useful signal in a background
  task.
- `commit.gpgsign=true` with SSH signing. Verified non-interactively in a scratch
  repo *before* delegating — a passphrase-locked key would have hung every background
  worker on an invisible prompt rather than erroring.
- `gh` was authenticated as a **different account** (`hamzaanwar-wamo`) than the
  repo owner (`hamzaanwar12`); the API reported `push: false`. Every `git push` and
  `gh pr create` would have 403'd after the work was already done.
- `worktree.baseRef` defaults to branching from `origin/<default-branch>`, which does
  not exist here — the remote is empty. Set to `head` so worktrees branch from the
  local integration branch instead.

Lesson applied: audit the delegation substrate before delegating, not after the
first failure. A background agent's failure is much quieter than a foreground one's.

#### Correction 2 — the deny-list I wrote was decorative

I generated `.claude/settings.json` with a broad allowlist plus a deny list of
destructive git operations, and it looked right. An automated security review
flagged three holes, all of which I had written and none of which I had noticed:

- `Bash(python*)` was allowed, so `python -c "import subprocess; ..."` re-enabled
  every single denied operation. Same for `node -e`, `npx`, `uv run`.
- `Bash(git push*)` was allowed and `Bash(git push --force*)` denied -- but these
  rules are *prefix* matches, so `git push origin main --force` matched the allow
  and never matched the deny. The guardrail was inert for the exact command it
  existed to stop.
- `Bash(curl -s localhost*)` matched `localhost.evil.com`, because prefix matching
  does not stop at the host boundary.

Corrected by removing every bare interpreter wildcard, denying inline-exec forms
(`python -c`, `node -e`), narrowing `git push` to three exact safe spellings, pinning
curl past the `host:port` boundary, and denying agents write access to
`.claude/settings.json` so a worker cannot widen its own permissions.

Stated limit, since the allowlist should not be oversold: `npm run *` executes
whatever `package.json` defines, and the implementers write `package.json`. This is
protection against *accidental* destruction, not containment of a determined agent.

#### Correction 3 — vitest config in the wrong defineConfig

The generated `vite.config.ts` put a `test: {...}` block inside `defineConfig`
imported from `vite`. That type does not accept `test`, so `tsc -b` failed the
build. Fixed by importing `defineConfig` from `vitest/config`, which accepts both
the Vite and Vitest keys. Caught by running the build rather than assuming it.

#### Environment finding -- contested port 8000

Not an AI error, but worth recording because it would have been poisonous during a
recorded demo. An unrelated pre-existing process was already listening on `*:8000`.
Our uvicorn bound `127.0.0.1:8000` *successfully alongside it*, so both were live
and `curl localhost:8000/health` non-deterministically hit the other service -- it
answered with a JSON error shape that was not FastAPI's, which is what gave it away.
Two listeners on one port do not fail loudly; they fail confusingly. The API moved
to 8010 and the sole-listener check is now part of setup.

#### Correction 4 — my own ADR overstated what FORCE ROW LEVEL SECURITY buys

ADR 0002 (which I wrote) claimed `FORCE ROW LEVEL SECURITY` was one of two guards
against RLS being bypassed "by a table's owner or a superuser". The implementer
followed it faithfully and its tests passed. Verifying the claim myself rather than
trusting it, I connected as the Docker superuser with `relforcerowsecurity = true`
and got **every row back**.

`FORCE` closes the *table owner* bypass only. A superuser or a `BYPASSRLS` role
bypasses RLS unconditionally and `FORCE` does nothing about it. The real guarantee is
that the API connects as `techforce_app`, which is `rolsuper = false` and
`rolbypassrls = false` — confirmed from `pg_roles`. `FORCE` is a narrower second
guard for the case where the app role is later made the table owner.

This is the most dangerous class of error in the whole exercise: a security claim
that is *almost* right, in a document other agents are told to treat as authority,
where every test still passes. Corrected in ADR 0002 with the verification output.

Verified independently, as `techforce_app`, not through the API:

| probe | result |
|---|---|
| no `app.recruiter_id` set | 0 rows — fails closed |
| `R-103` (PH-MNL\|CO-BOG) | only `CO-BOG`, `PH-MNL` |
| `R-101` (admin) | all four regions |
| `R-999` (unknown id) | 0 rows |
| `set_config` with `'; DROP TABLE candidates; --` | stored as a literal, 0 rows, table intact |

#### Correction 5 — a catalog reading that was wrong, settled by experiment

Reviewing the policy I noted `polwithcheck IS NULL` and labelled it "writes
unconstrained". Wrong: for a `FOR ALL` policy PostgreSQL reuses the `USING`
expression as the write check. Tested instead of inferred — as `techforce_app` with
`R-103`, inserting a `US-MW` Candidate is rejected with *"new row violates
row-level security policy"*, while a `PH-MNL` insert succeeds. Writes are
region-fenced too, which is stronger than the brief requires. Recorded in ADR 0002
along with its consequence for the import path.

#### Correction 6 — a hardcoded credential in a migration

The generated migration contained `CREATE ROLE techforce_app LOGIN PASSWORD
'techforce_app'` — a credential in version control, identical on every machine that
ever runs it. Now read from a required `TECHFORCE_APP_PASSWORD`, failing loudly if
absent rather than falling back to a literal.

The fix had a second-order problem worth noting: `CREATE ROLE` is a utility
statement, so PostgreSQL accepts no bind parameter for the password, and a `DO`
block takes no parameters either. The first attempt (`PASSWORD :pw`) would not have
bound at all. Resolved by having PostgreSQL escape the value itself via
`quote_literal()` — bound as a parameter on the way in — rather than hand-rolling
quoting around a secret.

#### Correction 7 — an entire field silently dropped, with 69 tests green

This is the one I would lead with. `Candidate` declared `legacy_candidate_id`, the
CSV column is `candidate_id`, and nothing mapped them. Pydantic ignored the unknown
key, so **all 44 valid rows parsed with `legacy_candidate_id = None`** — every
Candidate lost its traceability back to the source export, which ADR 0001 exists to
preserve.

The whole suite was green. It stayed green because every test constructed
`Candidate(legacy_candidate_id=...)` **directly**, so nothing in 69 tests ever
crossed the CSV→model boundary where the mapping lives. The tests validated the
model against itself.

Found by running the real fixture end to end and checking an acceptance criterion
numerically: "two Candidates carry `C-1010`" returned `None`, not `2`. Fixed with
`Field(alias="candidate_id")` plus `populate_by_name=True` so direct construction
still works, and added a test that validates from a raw CSV-shaped dict — the
boundary the suite was missing.

Lesson: a passing suite says the code agrees with the tests. It says nothing about
whether either agrees with the input. Drive at least one test from the real artefact.

#### Correction 8 — a count that the fixture could never falsify

`MergeOutcome.is_merge` was a boolean per email. But the Import Report counts
**rows**: an email appearing three times is one Import and *two* Merges. A boolean
reports one.

No email in `candidates_import.csv` appears more than twice, so the fixture cannot
expose this and no test would ever have failed. Changed to `merged_rows: int` with
`is_merge` derived from it, and added the three-row case explicitly — a test the
fixture does not motivate but the specification does.

#### Correction 9 — my own row count was wrong

I recorded "54 data rows" in the spec, from `wc -l`. It is **53**: row C-1050's
quoted notes field spans three physical lines, so physical lines are not rows. The
same assumption in code — splitting the upload on newlines — would corrupt C-1050
and every row after it. Corrected in the spec; the parser uses the `csv` module.

Verified import numbers against the real file: 53 Source Rows → 44 valid, 9
rejected (exactly the 3 email failures, 1 impossible date, 3 region failures, 2
status failures), folding to 41 Candidates = 38 Imports + 3 Merges.

#### Correction 10 — an Import Report that did not account for its input (my error, propagated)

The import endpoint reported `imported=38, merged=3, rejected=9` on the fixture.
38 + 3 + 9 = **50**, against 53 Source Rows. Three rows simply vanished from the
accounting.

Cause: a Candidate new to the database but folded from several Source Rows credited
only its *extra* rows as Merges, never crediting the first row as an Import. The
implementation's own docstring described the correct rule ("one Import plus one
Merge per extra row") while the code below it did something else.

**The 38 came from me.** My verification script counted `sum(1 for o in outcomes if
not o.is_merge)` — candidates with no merge — and I then handed "38 imported" to the
implementer as an acceptance number. It built to my number faithfully and its tests
locked the error in. The lesson is about delegation, not about this bug: a number
supplied to an agent as ground truth stops being checked. Derive the invariant and
let the agent satisfy it, rather than handing over a figure.

Fixed so every Source Row has exactly one outcome, and added the invariant as an
assertion rather than a comment:

    imported + merged + len(rejected) == number of Source Rows

Verified on the live API: first import `41 + 3 + 9 = 53`; re-uploading the same file
`0 + 44 + 9 = 53` with the Candidate count unchanged at 41.

#### Correction 11 — blocking I/O on the event loop, and an unbounded upload

Three further defects in the endpoint, flagged by security review:

- The handler was `async def` but did blocking work — psycopg I/O and CSV parsing —
  which runs **on** the event loop and stalls every other request for the duration
  of an import. Changed to a plain `def`, which FastAPI runs in a threadpool. This
  is a quietly common FastAPI mistake: it is correct-looking, passes every test, and
  only shows up as mysterious latency under concurrency.
- The upload was read unbounded into memory. Now capped, returning 413.
- The batched upsert put every row in one `VALUES` list. PostgreSQL allows at most
  65535 bind parameters per statement, so at 12 columns the import would have failed
  above ~5460 rows — well inside "a real client export". Now chunked by that limit,
  with every chunk inside the same transaction so the import stays all-or-nothing.

## Security posture, and exactly where it stops

Worth separating two axes that get conflated, because the brief simplifies one and
not the other:

**Authentication — who is asking — is deliberately fake.** `X-Recruiter-Id` is an
unverified, client-supplied header. Anyone who can reach the API can claim to be
Dana and import Candidates. The brief specifies this ("simplified auth — no login
flow needed") so it is a requirement, not an oversight, and an automated security
review flagged it exactly as it should. In production this is a verified credential
— a signed token whose claims yield the recruiter id, or a gateway that authenticates
the user and strips any client-supplied copy of the header — and nothing else about
the design changes, because the identity enters at one place (`app/deps.py`).

**Authorization — what that caller may see — is real and is enforced in the
database.** This is the part the exercise is actually testing, and it does not
depend on the header being trustworthy:

- The region fence is a PostgreSQL RLS policy, not a `WHERE` clause an endpoint
  remembers to add. A future endpoint that forgets to scope returns nothing.
- The policy resolves Assigned Regions **itself** from `recruiter_regions` and
  `is_admin`. The application passes only an identifier, so an application bug
  cannot widen anyone's visibility by passing the wrong region list.
- The API connects as `techforce_app`: `rolsuper=false`, `rolbypassrls=false`,
  not the table owner. This — not `FORCE ROW LEVEL SECURITY` — is what actually
  makes the policy apply. See Correction 4.
- Writes are fenced too, not just reads (Correction 5).
- `total` is computed inside the scoped transaction, so the row count cannot leak
  the global figure while `items` looks correct.

So: trusting the header lets a caller choose *which* recruiter they are. It does not
let them see outside whatever that recruiter is permitted to see, and it cannot be
widened from application code. Promoting the header to a verified credential is a
self-contained change; moving authorization out of the data layer would not be.

Other deliberate limits:

- Dev credentials are committed in `docker-compose.yml` and `.env.example` so setup
  works from a clean machine. The application role's password is **not** — it comes
  from `TECHFORCE_APP_PASSWORD` and the migration fails loudly without it
  (Correction 6).
- `recruiters` and `recruiter_regions` carry no RLS and are readable by
  `techforce_app`, because the policy's own lookup needs them. A recruiter could
  therefore read the roster. The roster is not Candidate data and the brief treats
  it as a fixture, so this is accepted rather than fixed.
- Rate limiting, audit logging, and CSRF are absent; there is no browser session to
  forge and no multi-tenant boundary beyond Region.

#### Correction 12 — a documented limitation whose own example was wrong

I had written that `search=sofia` would not match `Sofía Cárdenas` because there is
no accent folding. Checking it against the running API: it returns her. Her email is
`sofia.cardenas@hotmail.com`, and `search` covers the email column, so ILIKE matched
there. The limitation is real; my example of it was not.

The accurate example is `muller` vs `Müller`, whose email is `jurgen.mueller@gmail.com`
and therefore offers no ASCII echo — verified `muller` → 0, `Müller` → 1,
`mueller` → 1. Corrected in both the spec and the future-work list.

Also recorded because it briefly fooled me the other way: `search=Trần` returns
nothing, which looks like a Unicode bug. It is not — `C-1044` has region `USW` and
is one of the nine rejected rows, so he was never imported. And `tran` returns
`Rachel Ostrander`, matching the substring in her surname. Both correct; neither
obvious from the output alone.

Worth stating plainly: a documented known-limitation is still a claim, and an
unverified one is just a comment that sounds authoritative.

#### Correction 13 — a stale-response race, and a regression test that proved nothing

`useCandidates` aborts the previous request before issuing a new one and checks
`controller.signal.aborted` before using the response. But the check sat *before*
`await res.json()`, and nothing re-checked after it. Parsing the body yields
control, so a newer request can abort the controller during that window and the
older response then paints — rendering the previous recruiter's Candidates, which
on screen is indistinguishable from an authorization bug. Added a second check
after the await.

The more useful half of this entry is what happened next. My first regression test
reproduced "the response arrives after an abort", passed, and I nearly moved on.
Then I removed the fix and **it still passed** — the pre-await check already covered
that scenario, so the test demonstrated nothing and would have sat in the suite
looking like protection.

The window is narrower than I first described: it needs the abort to land *during*
body parsing, not before the response. Rewritten with a `json()` that resolves
slowly, which fails without the guard (`CalebOnly` paints) and passes with it —
verified in both directions.

Caveat recorded rather than glossed: with real `fetch`, aborting mid-`json()`
normally rejects the body promise and lands in the `.catch`, so this is less
reachable in a browser than in a mock. The guard is one line and costless; the
reasoning is worth more than the fix.

Lesson, and it generalises past this codebase: **a regression test is only evidence
if you have watched it fail.** Every test added here for a defect was run against
the unfixed code first.

#### Correction 14 — my own fix silently changed the API contract

Correction 7 added `Field(alias="candidate_id")` so the CSV column would populate
`legacy_candidate_id`. That fixed the import. It also broke the API, because a plain
`alias=` in Pydantic v2 applies on the way **out** as well, and FastAPI serializes
response models with `by_alias=True` by default. So the list endpoint started
returning `candidate_id` instead of `legacy_candidate_id`.

The frontend read `c.legacy_candidate_id` and got `undefined` — for every row. And
`tsc` was clean throughout, because the frontend's `Candidate` interface is a
hand-written assertion about the server's shape, not a check of it. A typed
frontend against an untyped contract gives you the feeling of safety and none of it.

Fixed with `validation_alias="candidate_id"`, which scopes the alias to input and
leaves the response using the glossary's name. Added two tests that pin the response
field names — the boundary that was unprotected. Verified both fail under the old
plain `alias=` and pass after.

Found by the Spec axis of the code review, chasing a different bug (below).

#### Correction 15 — a React key on a deliberately non-unique field

`CandidateView` used `key={c.legacy_candidate_id}`. ADR 0001 states plainly that the
legacy id is **not** an identity — the fixture reuses `C-1010` for two different
people. The admin view contains both of them (ids 10 and 41), so this produced
duplicate keys, and React silently misrenders rows on re-order or filter rather
than erroring.

Compounded by Correction 14: because the field was `undefined` in the response,
*every* row shared the key `undefined`, not just the two colliding ones.

Keyed on `id` instead, the server's stable row identity, and added a test asserting
the two `C-1010` rows carry distinct ids. Two independent mistakes landed on the same
line, and the second hid the first.

#### Correction 16 — narrowing a standard I wrote, instead of obeying it

The Standards axis flagged a hard violation: `GLOSSARY.md` said *"Do not call either
one 'status' unqualified"*, and the code uses bare `status` in both layers.

Correct against the letter of the rule. But the brief specifies the URL —
*"Build `GET /api/v1/candidates?search=&status=`"* — so that parameter cannot be
renamed, and the frontend contains no Import Outcome concept for `status` to be
ambiguous with. Obeying the rule meant renaming an externally fixed API parameter.

So I narrowed the rule to what it actually protects against: qualify the term in
prose and wherever both concepts are in scope, and record the three places where the
bare name is fixed from outside. Worth logging because the reflex under review
pressure is to comply with the written standard; sometimes the standard is the
defect, and a rule broader than its problem generates busywork that looks like rigor.

Also from the Standards axis, both applied: the response models moved out of
`db.py` into `schemas.py` (they were only there because a ticket forbade touching
`schemas.py`), and the duplicated `set_config` call became one
`_set_recruiter_scope` helper — worth it less for the duplication than because it
makes a single place responsible for keeping the recruiter id a bound parameter.

## What I'd do next with more time

- **Accent-insensitive search.** Verified: `muller` does not match `Müller`. Needs
  the `unaccent` extension plus a functional index. Note the limitation is narrower
  than it first appears -- `sofia` *does* find `Sofía Cárdenas`, but only because
  `search` also covers the email column and hers is `sofia.cardenas@hotmail.com`.
  It bites exactly when the email offers no ASCII echo of the accented name.
- **Identity-merge workflow.** Email is the candidate identity, so a candidate who
  changes email becomes a new record. A production system needs an explicit merge.
- **Audit logging** on imports and on scoped reads.
- **Containerized CI** running the suite, linting, and type checks before merge.
- **Index tuning** for the RLS policy's per-row subquery at realistic scale.
