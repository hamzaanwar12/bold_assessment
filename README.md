# TechForce — Candidate Import & Scoped Recruiter View

A vertical slice of the TechForce recruiting platform: import a messy candidate CSV
into PostgreSQL, expose it through a region-scoped API, and drive it from a React
table where a recruiter sees only their assigned regions.

**Authorization is enforced in the database**, by a PostgreSQL Row-Level Security
policy — not by a `WHERE` clause the endpoint remembers to add, and not in the UI.
See [`docs/adr/0002-rls-for-region-scoping.md`](docs/adr/0002-rls-for-region-scoping.md).

- Design decisions and the AI usage log: [`NOTES.md`](NOTES.md)
- Domain vocabulary: [`GLOSSARY.md`](GLOSSARY.md)
- Spec and ticket graph: [`.scratch/candidate-import-scoped-view/`](.scratch/candidate-import-scoped-view/)

## Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Docker | 29.7 | PostgreSQL only; the app runs on the host |
| [uv](https://docs.astral.sh/uv/) | 0.13 | Installs Python 3.12 itself — no system Python needed |
| Node | 26 | Any version supporting Vite 7 |

## Setup

### 1. Environment

```bash
cp .env.example .env
```

`.env` holds **two** database URLs, deliberately:

- `DATABASE_URL_OWNER` — runs migrations and the seed. This role owns the tables.
- `DATABASE_URL_APP` — the only connection the API uses. A non-owner,
  non-superuser role that the RLS policy actually applies to.

It also sets `TECHFORCE_APP_PASSWORD`, which the migration requires to create the
application role. The migration fails loudly if it is unset rather than falling
back to a committed literal.

> The database credentials in `docker-compose.yml` and `.env.example` are
> development throwaways, committed so setup works from a clean checkout.

### 2. PostgreSQL

```bash
docker compose up -d
```

Starts PostgreSQL 16 on **127.0.0.1:5433** (loopback only) and creates two
databases: `techforce` and `techforce_test`. The test suite uses its own database,
so running tests never destroys data you are looking at.

### 3. Backend

```bash
cd backend
uv sync                                  # installs Python 3.12 + dependencies
set -a && . ../.env && set +a            # load the connection URLs
uv run alembic upgrade head              # schema + app role + RLS policy
uv run python -m app.seed                # the 5 recruiters from data/recruiters.csv
uv run uvicorn app.main:app --port 8010
```

**Port 8010, not 8000** — 8000 was occupied by an unrelated service on the
development machine, and two listeners on one port route non-deterministically.

Interactive API docs: <http://localhost:8010/docs>

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default <http://localhost:5173>). The dev server proxies
`/api` to `http://localhost:8010`, so the browser sees one origin and the backend
needs no CORS middleware.

## Importing the candidates

Import is **Admin-only**. `R-101` (Dana Whitmore) is the only admin in the roster.

```bash
curl -X POST http://localhost:8010/api/v1/candidates/import \
  -H "X-Recruiter-Id: R-101" \
  -F "file=@data/candidates_import.csv;type=text/csv"
```

Expected on the supplied fixture:

```json
{ "imported": 41, "merged": 3, "rejected": [ … 9 rows … ] }
```

`imported + merged + rejected` always equals the number of data rows (53 here):
every Source Row has exactly one outcome. Re-running the same import is safe and
yields `imported: 0, merged: 44` — the Candidate count stays at 41.

The 9 rejected rows are data rows 34, 35, 36, 41, 45, 46, 48, 49 and 53 — three
email failures, one impossible calendar date, three unresolvable regions, and two
unrecognised statuses. Rejection reasons are in the response.

## Seeing the scoping work

```bash
# Dana (admin) sees every region
curl -s "http://localhost:8010/api/v1/candidates?page_size=100" -H "X-Recruiter-Id: R-101" | jq '.total'   # 41

# Marisol sees only PH-MNL and CO-BOG
curl -s "http://localhost:8010/api/v1/candidates?page_size=100" -H "X-Recruiter-Id: R-103" | jq '.total'   # 9

# An unknown recruiter is refused, not given an empty list
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:8010/api/v1/candidates" -H "X-Recruiter-Id: R-999"   # 403
```

In the UI, switch recruiter in the dropdown and the rows change.

### Proving the control is in the database, not the API

The point of RLS is that the guarantee survives the application being wrong. Check
it with the API out of the picture entirely:

```bash
docker compose exec -e PGPASSWORD=techforce_app db \
  psql -U techforce_app -d techforce -c \
  "SELECT set_config('app.recruiter_id','R-103',false); SELECT DISTINCT region_code FROM candidates;"
```

Only `CO-BOG` and `PH-MNL` come back. With no `app.recruiter_id` set, zero rows do
— it fails closed. Note that connecting as the owner role (`techforce`) returns
everything, because it is a superuser and superusers bypass RLS unconditionally;
that is exactly why the API uses `techforce_app`.

## Tests

```bash
# Backend — 121 tests
cd backend && set -a && . ../.env && set +a && uv run pytest -v

# Frontend — 4 tests
cd frontend && npm test
```

The backend suite migrates `techforce_test` itself and rolls each test back, so it
is safe to run at any time.

## Layout

```
backend/
  app/
    normalizers.py   pure field normalization and the rejection boundary
    schemas.py       Pydantic v2 — what a valid Candidate is
    dedup.py         in-memory folding on normalized email
    db.py            the only Candidate read path, plus the batched write
    deps.py          recruiter resolution, 403s, the Admin guard
    routers/         the two endpoints
    seed.py          recruiter roster
  alembic/versions/  schema + app role + RLS policy, in one revision
frontend/src/
  useCandidates.ts   fetch + AbortController, no data-fetching library
  CandidateView.tsx  table, search, status filter, recruiter switcher
docs/adr/            the two decisions worth recording
data/                the supplied fixtures
```
