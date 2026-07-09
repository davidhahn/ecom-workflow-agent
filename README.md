# ecom-workflow-agent

Enterprise Operations Intelligence Agent — an eCommerce ops assistant. See [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions.

## Structure

```
apps/web       Next.js 16 + TypeScript + Tailwind frontend
apps/api       Python 3.14 + FastAPI backend (poetry)
packages/shared  Generated TS types (openapi-typescript output, not hand-written)
```

## Tooling

Workspaces are managed with **pnpm** (not npm) — pnpm's content-addressable store and stricter symlinked `node_modules` avoid the phantom-dependency issues plain npm workspaces allow, which matters once `apps/web` starts importing from `packages/shared`.

`apps/api` is managed separately with **Poetry**, since it's a Python package outside the JS workspace graph.

## Setup

Install JS dependencies (web + shared):

```bash
pnpm install
```

Install the API's dependencies:

```bash
cd apps/api
poetry install
```

Start the database:

```bash
docker compose up -d
```

This brings up a single `postgres` service (image `pgvector/pgvector:pg17`) with the `vector` extension available, listening on `localhost:5432`. No app services are wired into compose yet.

Copy the env templates and fill in real values:

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

## Database

Apply migrations and load fixture data (from `apps/api`, with Postgres up and `.env` configured):

```bash
poetry run alembic upgrade head
poetry run python -m app.db.seed
```

Schema is defined via SQLAlchemy models under `apps/api/app/db/models.py`; migrations live in `apps/api/alembic/versions/`. `seed.py` is re-runnable — it truncates and reseeds the six Part 1 tables (customers, products, orders, order_items, refunds, support_tickets) with deterministic fixture data.

## Running the apps

```bash
# API (from apps/api)
poetry run uvicorn app.main:app --reload --port 8000

# Web (from repo root)
pnpm --filter web dev
```

The API exposes a health check at `GET /health`, its OpenAPI spec at `/openapi.json`, the SQL analysis path at `POST /query/sql` (`{"question": "..."}`), and the RAG retrieval path at `POST /query/rag` (`{"question": "...", "k": 3}`) — see `apps/api/README.md` for both. RAG needs its policy corpus ingested first: `poetry run python -m app.rag.ingest` (from `apps/api`).

## Codegen: OpenAPI → TypeScript

`packages/shared` contains only generated TypeScript — nothing there is hand-written. With the API running (`poetry run uvicorn app.main:app --port 8000`), regenerate the types by running, from the repo root:

```bash
pnpm run codegen
```

This runs `openapi-typescript http://localhost:8000/openapi.json -o src/generated.ts` inside `packages/shared`, pulling the live OpenAPI spec from the running FastAPI app. Re-run it any time the API's routes or schemas change; never edit `packages/shared/src/generated.ts` by hand.
