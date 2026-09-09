# Setup and deployment

This guide covers local setup and the repository's deployment configuration. For endpoint behavior, see the [API guide](../apps/api/README.md). The [architecture](../ARCHITECTURE.md) explains how the services fit together.

## Prepare your environment

Install Python 3.14, Poetry, Node.js, pnpm, and Docker. The repository pins pnpm in [package.json](../package.json). Postgres 17 with pgvector runs through [Docker Compose](../docker-compose.yml).

Start from the repository root:

```bash
pnpm install
docker compose up -d
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

Copy the templates on first setup; copying them again replaces existing local settings. Keep credentials in the ignored `.env` files.

Configure these values before running migrations or starting the apps:

| Setting | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | API | Main database connection; the template matches the default local Compose database |
| `OPS_AGENT_DB_PASSWORD` | API | Password for the restricted SQL role |
| `REFUND_EVALUATOR_DB_PASSWORD` | API | Password for the restricted refund role |
| `ANTHROPIC_API_KEY` | API | Required for live Claude calls |
| `EMBEDDING_PROVIDER` | API | `local` for BAAI/bge-m3 or `voyage` for hosted embeddings |
| `VOYAGE_API_KEY` | API | Required when using `voyage` |
| `INTERNAL_PROXY_SECRET` | API and web | Set the same secret in both apps |
| `NEXT_PUBLIC_API_URL` | Web | API base URL; locally, `http://localhost:8000` |

Use distinct generated passwords for the database roles. Their migrations require the configured values. Changing a password in `.env` alone does not update an existing database role.

Local embeddings need memory and an initial model download. Production uses Voyage. Use the same provider for ingestion and querying; switching providers requires re-ingestion and retrieval verification.

## Prepare the database

Run from `apps/api`:

```bash
poetry install
poetry run alembic upgrade head
poetry run python -m app.db.seed
poetry run python -m app.rag.ingest
```

Migrations create the schema and restricted roles. The seed script replaces nine business tables, including shipments and campaign data, using `TRUNCATE ... CASCADE`. Run it against the intended demo database; it replaces records created during earlier demo sessions in those tables and can affect dependent records.

Ingestion separately replaces `policy_chunks` with passages from the documents listed in [ingest.py](../apps/api/app/rag/ingest.py). It needs a working embedding provider.

## Start and verify the apps

In one terminal, from `apps/api`:

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

In another terminal, from the repository root:

```bash
pnpm --filter web dev
```

Open the frontend at `http://localhost:3000`. Check the API process with:

```bash
curl http://localhost:8000/health
```

A healthy response is `{"status":"ok"}`. This checks reachability; it does not exercise the database or model. Run a scenario in the frontend to verify a complete request, then inspect its log in System Traces.

The frontend sends `/api/*` requests through its server-side proxy. That proxy adds `X-Internal-Proxy-Secret` before forwarding to the backend. Direct API requests, including `/docs` and `/openapi.json`, require the same header. `/health` is exempt.

## Run checks

From the repository root:

```bash
pnpm --filter web test
pnpm --filter web lint
pnpm --filter web build
```

The frontend build fetches Google Fonts and needs network access for that step.

From `apps/api`:

```bash
poetry run pytest
poetry run python ../../evals/run.py --subset deterministic
```

Some pytest tests make live model calls. The deterministic evaluation subset runs 18 cases without live model calls, using the prepared application environment. See [Running evaluations](../evals/README.md) for full runs and output interpretation.

## Regenerate frontend types

The frontend consumes generated API types from `packages/shared`. Regenerate them when API routes or schemas change; leave the generated file unedited by hand.

The existing `pnpm run codegen` script targets the API directly and does not supply its required secret header. With both local apps running, use the frontend proxy instead. Run from the repository root:

```bash
pnpm --filter shared exec openapi-typescript http://localhost:3000/api/openapi.json -o src/generated.ts
```

The proxy supplies the secret from the web environment. Review the generated diff and rebuild the frontend afterward.

## Deploy the backend

[render.yaml](../render.yaml) declares the API service, a Postgres database, and a daily reseed job. It sets the API root to `apps/api`. The pre-deploy command runs migrations and policy ingestion; the start command launches Uvicorn on the assigned port.

Create a Render Blueprint from the repository and review the declared resources. Configure the required environment before a successful deployment:

- `DATABASE_URL` comes from the Blueprint's database connection.
- `OPS_AGENT_DB_PASSWORD` is generated by the Blueprint.
- Supply `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, and `INTERNAL_PROXY_SECRET` through the service environment. Ingestion needs the Voyage key during pre-deploy.
- Add `REFUND_EVALUATOR_DB_PASSWORD` manually. The current Blueprint omits it, but the refund-role migration and application require it. Use the password matching that role if it already exists.

Production sets `EMBEDDING_PROVIDER=voyage`. After migrations complete, seed the business fixtures once from the API service environment if the database is new:

```bash
poetry run python -m app.db.seed
```

The separate reseed job runs daily at 06:00 UTC. Application deploys reload policy passages but do not reseed business records. Check the deployment output for successful migrations and ingestion, then verify `/health`.

## Deploy the frontend

Deploy the same repository to Vercel with `apps/web` as the project root. Keep the rest of the monorepo available during the build: the frontend imports the shared package and reads committed evaluation reports outside its directory.

Set `NEXT_PUBLIC_API_URL` to the deployed API's base URL. Set the server-only `INTERNAL_PROXY_SECRET` to the same value used by the API, then deploy and run a scenario.

The backend's [origin allowlist](../apps/api/app/main.py) already contains `https://ecom-workflow-agent-web.vercel.app`. Update it if deploying under a different frontend domain. CORS controls browser origins; the proxy secret controls access to backend requests. Neither establishes an end user's identity.

Secret rotation requires updating both hosting environments and redeploying as needed. Never give the shared secret a `NEXT_PUBLIC_` prefix.

## When setup fails

| Symptom | Check |
|---|---|
| Migration fails while creating a role | Both role passwords are configured before migration |
| Health succeeds but requests return 403 | The web and API proxy secrets match, and the web proxy is being used |
| Refund requests fail to connect | The refund role exists and its password matches the API setting |
| Policy retrieval returns no passages | Ingestion completed using the selected provider; inspect relevance filtering too |
| A deployed policy answer differs from local results | Provider, corpus, and calibrated threshold match the environment under test |
| Code generation returns 403 | Use the local proxy command above with both apps running |

For request-level failures, use the [API debugging guide](../apps/api/README.md#inspect-a-failure). Production ranking and identity limitations are covered in [Architecture](../ARCHITECTURE.md).
