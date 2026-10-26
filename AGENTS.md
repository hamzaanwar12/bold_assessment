# TechForce Take-Home

A vertical slice of the TechForce recruiting operations platform: messy candidate CSV
→ PostgreSQL, exposed through a region-scoped API and a recruiter table view.

Stack: FastAPI + Pydantic v2 + SQLAlchemy 2.0 + PostgreSQL (backend), Vite + React +
TypeScript (frontend), pytest + Vitest (tests).

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, used verbatim as label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Git workflow

One ticket → one worktree → one PR, merged with a merge commit. See `docs/agents/git-workflow.md`.

### Frontend UI

Tailwind tokens, motion rules, and the DOM contract the tests rely on. See `docs/ui.md`.
