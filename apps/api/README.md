# API

FastAPI backend for the e-commerce operations assistant. It handles data and policy questions, evaluates refund requests, and supports ticket and invoice draft/confirm flows.

This guide covers running the API, using its endpoints, and inspecting failures. The [project overview](../../README.md) introduces the assistant; [Architecture](../../ARCHITECTURE.md) explains its request flow and execution controls.

## Run locally

Use Python 3.14 and Poetry, with Postgres running through the repository's Docker Compose configuration. Configure `apps/api/.env` from [.env.example](.env.example) before starting. Migrations need the database role passwords, and the API requires `INTERNAL_PROXY_SECRET` at startup. Model-backed requests need an Anthropic key.

Run these commands from `apps/api` against your local development database:

```bash
poetry install
poetry run alembic upgrade head
poetry run python -m app.db.seed
poetry run python -m app.rag.ingest
poetry run uvicorn app.main:app --reload --port 8000
```

Seeding replaces the business fixtures, including orders, shipments, and campaign data. Ingestion replaces the policy passages. Both commands reset their respective datasets when rerun.

`GET /health` checks that the API is reachable. Every other path requires an `X-Internal-Proxy-Secret` header matching the configured secret, including `/docs` and `/openapi.json`. The frontend proxy supplies this header; direct API clients must supply it themselves.

See [Setup and deployment](../../docs/DEPLOY.md) for the shared environment configuration and hosting instructions.

## Endpoints

The table describes changes to business records. Read paths also write audit or request logs.

| Endpoint | Purpose | Business data and permissions |
|---|---|---|
| `POST /query/analyze` | Answer a question using SQL and policy retrieval | Reads data; available to every demo role |
| `POST /query/sql` | Generate and execute a restricted SQL query | Requires read permission |
| `POST /query/rag` | Return relevant policy passages | Requires read permission |
| `POST /refund/evaluate` | Resolve a request and apply refund rules | Returns a decision without updating refunds; available to every demo role |
| `POST /tickets/draft` | Prepare a support ticket | Requires read permission; keeps an in-memory draft |
| `POST /tickets/confirm` | Confirm a ticket draft | Requires write permission; inserts the ticket |
| `POST /invoices/draft` | Prepare a vendor invoice | Requires read permission; keeps an in-memory draft |
| `POST /invoices/confirm` | Confirm an invoice draft | Requires write permission; validates before insertion |
| `GET /observability/requests` | List and filter request logs | No demo-role check |
| `GET /observability/requests/{request_id}` | Inspect one request | No demo-role check |

Permissions come from `X-Demo-Role`. The `read_only_viewer` and `support_agent` roles can read and draft. `manager` and `admin` can also confirm writes. Missing or invalid roles default to `read_only_viewer`.

These roles demonstrate permission behavior. They do not verify identity or isolate tenants. The proxy secret also does not establish who the end user is.

Use the OpenAPI schema for request and response fields. The [tool registry](app/tools/registry.py) and [permission dependency](app/permissions.py) define the tool permissions.

## How requests behave

### Combined questions

Send `{"question": "..."}` to `/query/analyze`. Claude chooses between SQL and policy retrieval inside a loop capped at four rounds, then writes an answer from the results.

The orchestrator reuses the query and retrieval services. After generation, grounding checks compare cited policy names and numbers with retrieved passages. Topic coverage checks can also flag unsupported subjects. Warnings leave the answer visible; a matching citation does not prove the policy was interpreted correctly.

### Direct SQL and retrieval

`/query/sql` accepts `{"question": "..."}`. Generated SQL passes statement and access checks, receives a row limit if needed, and undergoes an estimated-cost check. Execution uses the restricted `ops_agent_readonly` database role. SQL audit records capture attempts and their outcomes.

`/query/rag` accepts `{"question": "...", "k": 3}` and returns passages with source metadata. A relevance threshold filters the candidates. This endpoint returns evidence without generating an answer.

Ingestion reads the four documents listed in [ingest.py](app/rag/ingest.py), covering policy and campaign context. Local embeddings use `BAAI/bge-m3`; production uses Voyage AI. Thresholds differ by provider, and a known production ranking failure remains open. Use the [evaluation methodology](../../evals/methodology.md) when comparing retrieval changes.

### Refunds and confirmed writes

`/refund/evaluate` accepts `{"request_text": "..."}`. Claude extracts the request details. Code resolves the order and applies refund rules in order, using the first matching rule. An unresolved request returns `could_not_process`.

The evaluator uses its own restricted database role and returns a decision. Ticket and invoice workflows use separate draft and confirm endpoints. Their drafts live in memory for ten minutes, so expiry or a process restart can require a new draft.

## Inspect a failure

Start with the response status and request log. `GET /observability/requests` supports filtering by request type and date, with limit/offset pagination. Fetch a request by ID for its details, or inspect it through the frontend's Activity page.

Analyze requests include tool-call traces. SQL audit records provide query validation details. Token usage and estimated cost are populated where supported model calls occur; empty fields on other paths do not indicate missing execution.

A rejected query never reaches execution. Loop exhaustion returns an incomplete response. Grounding warnings happen after generation, so inspect the cited passages when reviewing a flagged answer.

Live request logs do not yet record model and prompt versions. Keep that limitation in mind when reproducing behavior across deployments.

## Tests and evaluations

From `apps/api`, run:

```bash
poetry run pytest
poetry run python ../../evals/run.py --subset deterministic
```

Prepare the database and ingested corpus first. Some pytest tests call live model endpoints and need a working API key. The 18-case deterministic evaluation subset makes no live model calls.

Model-dependent evaluations run separately. See [Evaluation methodology](../../evals/methodology.md) for scoring and experiment setup, and [EVALS.md](../../EVALS.md) for category definitions and coverage gaps.

## Source map

| Area | Source |
|---|---|
| SQL generation and validation | [app/query](app/query/) |
| Policy retrieval and ingestion | [app/rag](app/rag/) |
| Analyze loop and refund rules | [app/orchestrator](app/orchestrator/) |
| Ticket and invoice flows | [app/tickets](app/tickets/), [app/invoices](app/invoices/) |
| Request logging | [app/observability](app/observability/) |
| Database schema and migrations | [app/db](app/db/), [alembic/versions](alembic/versions/) |

The [decision log](../../DECISIONS.md) records implementation choices and earlier investigations.
