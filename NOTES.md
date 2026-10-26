# NOTES

> **Living document.** Written as the work happens, not reconstructed at the end.
> The AI usage log below is appended to at the moment each event occurs.

## Dedup & merge rules

_(filled in as implemented — see `docs/adr/0001-email-as-candidate-identity.md`)_

## Normalization decisions

_(filled in as implemented — see `.scratch/candidate-import-scoped-view/spec.md`)_

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

## What I'd do next with more time

- **Accent-insensitive search.** `sofia` does not currently match `Sofía`; needs the
  `unaccent` extension plus a functional index.
- **Identity-merge workflow.** Email is the candidate identity, so a candidate who
  changes email becomes a new record. A production system needs an explicit merge.
- **Audit logging** on imports and on scoped reads.
- **Containerized CI** running the suite, linting, and type checks before merge.
- **Index tuning** for the RLS policy's per-row subquery at realistic scale.
