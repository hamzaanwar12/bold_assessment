# 01 — Scaffold the repo and bring up PostgreSQL

Status: resolved
Type: task
Blocked by: —
Spec: ../spec.md

## Goal

A clean-machine-reproducible skeleton: PostgreSQL in Docker, a FastAPI app that
starts and answers a health check, and a Vite + React + TypeScript app that renders.

## Scope

- `git init` and a first commit. The submission checklist requires meaningful commit
  history, so the repository must exist before any code does.
- `docker-compose.yml` with PostgreSQL only (see spec: Operational setup). Named
  volume, pinned major version, exposed port, credentials via environment.
- Two databases are needed — the application database and a separate test database
  (see spec: Test environment). Create the second one at container init.
- `backend/` — dependencies (FastAPI, Pydantic v2, SQLAlchemy 2.0, psycopg 3,
  Alembic, pytest), app package, settings read from environment with a committed
  example env file. A `GET /health` endpoint.
- `frontend/` — Vite React TS scaffold, with the dev-server proxy to the API already
  configured (see spec: Frontend). Vitest + React Testing Library installed now, so
  ticket 09 does not have to touch tooling.
- `.gitignore` covering virtualenvs, `node_modules`, `__pycache__`, `.env`.

## Acceptance

- `docker compose up -d` brings up PostgreSQL; both databases exist.
- The API starts and `GET /health` returns 200.
- The frontend dev server starts and renders a placeholder page.
- A request to a relative `/api/...` path from the browser reaches the API through
  the proxy (no CORS middleware configured — confirm by its absence).

## Notes

Do not add CORS middleware. The proxy is the decision; adding both means the CORS
configuration is dead code that looks like an intentional security posture.
