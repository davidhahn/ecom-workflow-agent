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

`EMBEDDING_PROVIDER` (apps/api/.env) controls where RAG's embeddings come from — see `DECISIONS.md` #8:
- **Dev:** `EMBEDDING_PROVIDER=local` (the default if unset) — local `BAAI/bge-m3`, no `VOYAGE_API_KEY` needed.
- **Deploy:** `EMBEDDING_PROVIDER=voyage` — hosted Voyage AI, requires `VOYAGE_API_KEY`.

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

The API exposes a health check at `GET /health`, its OpenAPI spec at `/openapi.json`, the SQL analysis path at `POST /query/sql`, the RAG retrieval path at `POST /query/rag`, two orchestrator flows built on top of both — `POST /query/analyze` (combined SQL + RAG with a structural groundedness check) and `POST /refund/evaluate` (natural-language refund request → decision, no DB mutation) — and a unified request log across all four at `GET /observability/requests` (filter/paginate only, no aggregation) — see `apps/api/README.md` for all of it. RAG needs its policy corpus ingested first: `poetry run python -m app.rag.ingest` (from `apps/api`).

## Codegen: OpenAPI → TypeScript

`packages/shared` contains only generated TypeScript — nothing there is hand-written. With the API running (`poetry run uvicorn app.main:app --port 8000`), regenerate the types by running, from the repo root:

```bash
pnpm run codegen
```

This runs `openapi-typescript http://localhost:8000/openapi.json -o src/generated.ts` inside `packages/shared`, pulling the live OpenAPI spec from the running FastAPI app. Re-run it any time the API's routes or schemas change; never edit `packages/shared/src/generated.ts` by hand.

## Deployment

`render.yaml` (repo root) is a [Render Blueprint](https://render.com/docs/blueprint-spec) for **`apps/api` only** — it defines the FastAPI web service, the Postgres database, and a daily reseed cron job, all Starter tier. It is not committed to trigger anything automatically; deploying is a manual step:

1. In the Render dashboard: **New → Blueprint**, connect this GitHub repo. Render finds `render.yaml` at the repo root and shows the three resources it defines (`ecom-ops-api`, `ecom-ops-db`, `ecom-ops-reseed`) for review before creating anything.
2. Apply the blueprint. Render provisions the Postgres instance and deploys the web service — `preDeployCommand` runs `alembic upgrade head` against it before the new version takes traffic, every deploy, no exceptions (see the comments in `render.yaml`).
3. **After first deploy**, set the two secret env vars manually — they're declared as `sync: false` in `render.yaml`, meaning Render intentionally leaves them blank rather than expecting a value in the committed file: go to the `ecom-ops-api` service → **Environment**, and set `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` to real values. The service won't serve real requests correctly until both are set (`OPS_AGENT_DB_PASSWORD` doesn't need manual entry — Render generates it automatically on first deploy per `render.yaml`'s `generateValue: true`).
4. The `ecom-ops-reseed` cron job runs `python -m app.db.seed` daily at 06:00 UTC against the same database — independent of deploys, so an in-progress demo interaction isn't wiped by an unrelated code push (see the comment above it in `render.yaml`).

**`apps/web` (Next.js) is not part of this blueprint** — Render Blueprints don't drive Vercel deploys, and forcing a Next.js frontend into a Render web service would fight both platforms' conventions. Deploy `apps/web` to Vercel separately (connect the same repo, set the project root to `apps/web`, configure `apps/web/.env`'s variables — e.g. the API's base URL — in Vercel's dashboard); that config isn't written yet and would live in Vercel's own project settings or an `apps/web/vercel.json`, not here.
