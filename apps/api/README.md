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

1. **AST validation** (`app/query/validation.py`) — parses with `sqlglot`, rejects multi-statement input, non-SELECT statements, tables outside the 6 Part 1 tables, bare `SELECT *`, `customers.email`, and a function denylist (`pg_sleep`, `dblink`, `lo_import`/`lo_export`, `pg_read_file`, etc).
2. **Cost gate** (same file) — runs `EXPLAIN` and rejects if the estimated cost exceeds `QUERY_COST_THRESHOLD` (env var, default 10000); auto-appends `LIMIT 500` if the query has none.
3. **Database enforcement** (`alembic/versions/e226476acfd7_*.py`) — the app executes through a dedicated `ops_agent_readonly` role with column-level grants (not table-grant-then-revoke — see `DECISIONS.md` #6 for why that doesn't work), a 5s `statement_timeout`, and `default_transaction_read_only`.
4. **Audit log** (`app/query/audit.py` → `query_audit_log` table) — every attempt is logged regardless of outcome: the question, generated SQL, stated intent, and per-layer pass/fail.

Known gap, intentionally not built here: no row-level security or multi-tenant isolation — every caller sees the same rows subject to the column restrictions above.

## RAG query path

`POST /query/rag` (`{"question": "...", "k": 3}`) does top-k cosine similarity search over `docs/policies/*.md` and returns raw chunks — no LLM-generated answer, no groundedness check, no orchestrator yet. See `app/rag/`:

- **Chunking** (`app/rag/chunking.py`) — one chunk per H2 section (one numbered rule for `refund_policy.md`, one heading for `shipping_policy.md`/`support_playbook.md`), not fixed-size or semantic chunking. `source_doc` and `rule_number` are preserved as metadata.
- **Embeddings** (`app/rag/embeddings.py`) — local `sentence-transformers` (`BAAI/bge-m3`), no external embedding API; see the comment above the model init for why, and when to revisit it.
- **Storage** — `policy_chunks` table (`content`, `embedding vector(1024)`, `source_doc`, `rule_number`), no ANN index at this corpus size (~17 rows) — see `DECISIONS.md` #8.

Ingest (re-runnable — truncates and reinserts every time):

```bash
poetry run python -m app.rag.ingest
```

**Verification test (yours to run, not automated here):** query `"what's our policy on damaged shipments?"` and confirm rule 4 (damaged in shipping) ranks above rule 3 (changed mind) despite both mentioning timeframes; separately, query something that should surface rule 9 (clearance items) and confirm rules 2 and/or 5 appear somewhere in the top-3 — that's the actual test of whether `k=3` does the cross-reference job the policy doc's own text claims it does.
