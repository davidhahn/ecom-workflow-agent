# apps/api

FastAPI backend for the Ops Intelligence Agent. See the root [README](../../README.md) for monorepo-wide setup.

Run locally:

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Database

Schema is managed with SQLAlchemy models (`app/db/models.py`) + Alembic migrations (`alembic/versions/`), not hand-written SQL. With Postgres running (`docker compose up -d` from repo root) and `DATABASE_URL` set in `.env`:

```bash
poetry run alembic upgrade head    # apply migrations
poetry run python -m app.db.seed   # (re-)seed fixture data
```

`app/db/seed.py` is re-runnable — it truncates the six Part 1 tables and reinserts deterministic fixture data each time, so it's safe to run again after a schema change or reset.

The role/grant migration requires `OPS_AGENT_DB_PASSWORD` to be set in `.env` before running `alembic upgrade head` — it becomes the password for the restricted `ops_agent_readonly` Postgres role used by the SQL query path (see below). Generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`.

## SQL query path

`POST /query/sql` (`{"question": "..."}`) turns a natural-language question into a SQL query via Claude tool-calling, then runs it through four independent safety layers before executing — see `app/query/`:

1. **AST validation** (`app/query/validation.py`) — parses with `sqlglot`, rejects multi-statement input, non-SELECT statements, tables outside `ALLOWED_TABLES` (`app/query/constants.py`; the original 6 Part 1 tables plus `web_analytics`/`campaigns`), bare `SELECT *`, `customers.email`, and a function denylist (`pg_sleep`, `dblink`, `lo_import`/`lo_export`, `pg_read_file`, etc).
2. **Cost gate** (same file) — runs `EXPLAIN` and rejects if the estimated cost exceeds `QUERY_COST_THRESHOLD` (env var, default 10000); auto-appends `LIMIT 500` if the query has none.
3. **Database enforcement** (`alembic/versions/e226476acfd7_*.py`) — the app executes through a dedicated `ops_agent_readonly` role with column-level grants (not table-grant-then-revoke — see `DECISIONS.md` #6 for why that doesn't work), a 5s `statement_timeout`, and `default_transaction_read_only`.
4. **Audit log** (`app/query/audit.py` → `query_audit_log` table) — every attempt is logged regardless of outcome: the question, generated SQL, stated intent, and per-layer pass/fail.

Known gap, intentionally not built here: no row-level security or multi-tenant isolation — every caller sees the same rows subject to the column restrictions above.

## RAG query path

`POST /query/rag` (`{"question": "...", "k": 3}`) does top-k cosine similarity search over `docs/**/*.md` (policy docs plus `docs/notes/`) and returns raw chunks — no LLM-generated answer, no groundedness check, no orchestrator yet. See `app/rag/`:

- **Chunking** (`app/rag/chunking.py`) — one chunk per H2 section (one numbered rule for `refund_policy.md`, one heading for every other doc, including `docs/notes/campaign-launch-notes.md`), not fixed-size or semantic chunking. `source_doc` and `rule_number` are preserved as metadata.
- **Embeddings** (`app/rag/embeddings.py`) — provider selected by `EMBEDDING_PROVIDER` (`local` | `voyage`, default `local`); see `DECISIONS.md` #8. `local` uses `sentence-transformers` (`BAAI/bge-m3`), no external API, no key needed — the dev default. `voyage` calls the hosted Voyage AI API directly over HTTP (`voyage-3.5-lite`, `output_dimension=1024` pinned explicitly to match the column below) and requires `VOYAGE_API_KEY` — used in deploy, where `sentence-transformers`' `torch` dependency is a memory cost the environment can't absorb. Deliberately not the `voyageai` SDK: that package's own import graph pulls in `sentence-transformers`/`torch` whenever both are installed in the same environment (as they are here), which would defeat the point.
- **Storage** — `policy_chunks` table (`content`, `embedding vector(1024)`, `source_doc`, `rule_number`), no ANN index at this corpus size (~21 rows) — see `DECISIONS.md` #8.

Ingest (re-runnable — truncates and reinserts every time):

```bash
poetry run python -m app.rag.ingest
```

**Verification test (yours to run, not automated here):** query `"what's our policy on damaged shipments?"` and confirm rule 4 (damaged in shipping) ranks above rule 3 (changed mind) despite both mentioning timeframes; separately, query something that should surface rule 9 (clearance items) and confirm rules 2 and/or 5 appear somewhere in the top-3 — that's the actual test of whether `k=3` does the cross-reference job the policy doc's own text claims it does.

## Orchestrator: /query/analyze and /refund/evaluate

See `app/orchestrator/`. Both flows reuse the SQL and RAG paths' actual code, not simplified copies — `analyze_service.py` calls `execute_proposed_query` (the layers 1-4 pipeline `app/query/service.py` was split to expose, so a query Claude already proposed here doesn't need a second Claude call to re-derive it) and `app/rag/service.query_rag` directly.

**`POST /query/analyze`** (`{"question": "..."}`) — Claude picks `run_sql_query`, `search_policy`, both, or neither, across a bounded tool-use loop (max 4 iterations, parallel tool calls in one turn supported), then synthesizes an answer. The `tools=[...]` payload sent to Claude is built from `app/tools/registry.py` (`anthropic_tool_defs()`), not hand-written inline — see that module for the full registry entry per tool (input/output schema, permission level, error behavior), which exists so later tool-call tracing and multi-agent work can enumerate `TOOLS` generically instead of hardcoding tool names. `permission_required`/`requires_confirmation` are declared there but not yet enforced against anything. A structural groundedness check (`app/orchestrator/groundedness.py`) — regex + rule-title matching, not an LLM judge — parses the answer for rule citations (numeric, `"rule 9"`, or named, `"the final-sale exclusion"`) and cross-checks each against the `rule_number`s actually retrieved via `search_policy` in that request. An uncited-but-retrieved chunk is fine; a cited-but-not-retrieved rule sets `"grounded": false` and adds to `"ungrounded_claims"` — flagged, not blocked, since there's no remediation flow yet.

**`POST /refund/evaluate`** (`{"request_text": "..."}`, natural language) — two steps:
1. Claude (forced tool call, `app/orchestrator/refund_extraction.py`) extracts `product_identifier`, `customer_identifier`, `reason` (one of the 4 enum values), a `reason_confident` flag, and `evidence_submitted`. If `reason_confident` is false, or the product/customer can't be resolved to a real `order_item` (`resolve_order_item` in `refund_evaluator.py`), the response is `"status": "could_not_process"` — not one of the task's four decision statuses, added because "reject/flag rather than guess" needs *some* representation the schema didn't otherwise have.
2. `evaluate_refund()` (`app/orchestrator/refund_evaluator.py`) — zero LLM calls, checks real DB rows in a fixed order (first match wins): category exclusion (rule 9) → time window (rule 2/3, reason-specific) → evidence check (rule 4) → repeat-refund flag (rule 7) → approval threshold (rule 6) → otherwise approved (reason-specific rule). Returns a decision only; **never writes to `refunds`** — executing the decision is a real feature deliberately not built in Part 1.

Verified against both seeded edge cases: a Cotton Bath Towel Set `damaged_shipping` request with no evidence comes back **`denied`** (rule 4), and a Last-Season Winter Jacket `changed_mind` request comes back **`denied`** (rule 9). The evidence-check branch originally returned `pending` per the initial rule spec, but that implied a resolvable-later state Part 1 has no mechanism for (no evidence-upload or re-evaluation flow) — corrected to `denied`, since a one-shot decision with no persisted state can only accurately say the refund can't be processed *now*.

## Observability: request_log

See `app/observability/` and `app/db/observability_models.py`. Every call to all four endpoints above (`/query/sql`, `/query/rag`, `/query/analyze`, `/refund/evaluate`) writes exactly one `request_log` row — success or failure — via `request_log_span()`, a context manager that times the request and writes the row on exit regardless of how the block exits (normal return or unhandled exception; exceptions still re-raise after logging, never swallowed).

Per-type field population is intentionally uneven, not a bug: `input_tokens`/`output_tokens`/`estimated_cost_usd` are only set where an actual Claude call happened (none for `/query/rag`, which is local-embeddings-only); `grounded` is only meaningful for `analyze`; `sql_query_audit_id` (FK into `query_audit_log`) is only set when the request's own SQL path ran — including from inside `/query/analyze`, which reuses `execute_proposed_query()` directly rather than logging its own separate row (would violate "exactly one row per request"); `rag_chunks_retrieved` likewise only for `rag`/`analyze`.

Pricing (`app/observability/pricing.py`) is hardcoded per-token rates for the pinned model (`claude-sonnet-4-6`) with a comment flagging manual updates if the model changes — there's no live pricing API.

Read path — `GET /observability/requests` (`request_type`, `since`, `until`, `limit` [default 50, max 500], `offset`) — is filtering and pagination only, ordered by `created_at DESC`. Deliberately no aggregation/stats/grouping endpoint; that's Part 4 eval-harness work. `grounded` and `rag_chunks_retrieved` are kept as separate typed columns rather than folded into `output` specifically so Part 4 can query them directly instead of parsing them back out of an opaque blob.

**One real bug caught during verification:** `rag_chunks_retrieved` (a nullable JSONB column) initially stored the JSON literal `null` instead of true SQL `NULL` for every non-RAG request — SQLAlchemy's `JSON`/`JSONB` type defaults `none_as_null=False`, so a Python `None` serializes to JSON `null` rather than mapping to SQL `NULL` unless told otherwise. Fixed with `JSONB(none_as_null=True)`; re-verified with a raw `IS NULL` check, not just the ORM round-trip.

## Tests

`tests/test_tool_registry.py` is the first (only, so far) automated suite — it needs a live Postgres (seeded) and a working embedding model, since it deliberately exercises the real SQL and RAG pipelines rather than mocking them, to catch drift between a registry entry's `input_schema`/`output_schema` and what the tool actually accepts/returns:

```bash
poetry run pytest
```
