## Architecture Decisions

### Repo shape: monorepo

Monorepo (`apps/web`, `apps/api`, `packages/shared`). Two repos rejected:
no organizational split to justify it (sole dev, no separate deploy
cadence). Shared types generated from FastAPI's OpenAPI spec via
openapi-typescript into `packages/shared`, imported by both apps. Without
codegen this decision is a wash; with it, monorepo wins on every axis.
Codegen is not optional: skipping it reintroduces the exact drift problem
two repos would have had, with less visibility.

### Orchestration seam: LLM proposes, Python enforces

Claude extracts intent via structured tool-calling; a Python state machine
owns all execution authorization. LLM never executes directly.

The gate is two mechanisms, not one:

1. **Structural gate** (deterministic). SQL verb/table/column permission,
   refund threshold checks, approval routing. Unit-testable, binary pass/fail.
2. **Groundedness check** (heuristic). Verifies that rule numbers cited in a
   generated answer were actually present in the chunks retrieved for that
   request. Structural string/title matching, not semantic verification.

These are separate because they fail differently. A refund can pass every
structural check (correct amount, correct authorization tier, read-only
lookup) while resting on a misapplied or hallucinated policy clause. The
state machine cannot detect this; it has no visibility into meaning, only
structure. Treating groundedness as "one more rule in the same gate" was
considered and rejected: it would get implemented as a deterministic
check by default, which is the exact blind spot this split exists to avoid.

**Open**: PII column-scoping is partial, not general. `BLOCKED_COLUMNS` in
`app/query/constants.py` hardcodes a single exclusion (`customers.email`),
enforced by `_check_no_blocked_columns` in `validation.py` and independently
backed by column-level grants on the `ops_agent_readonly` role. The refund
evaluator uses a separate DB role that grants email instead of blocking it —
it only ever uses email to look a customer up, never to answer with, so the
same exclusion didn't apply. There is no general column-classification policy,
and no row-level isolation.

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | Python 3.14, FastAPI, uvicorn |
| Orchestration | Anthropic Python SDK (claude-sonnet-4-6) |
| Embeddings | `EMBEDDING_PROVIDER`-dispatched: local `sentence-transformers` BAAI/bge-m3 (dev default) or hosted Voyage AI `voyage-3.5-lite` at 1024 dims (deploy). See DECISIONS.md #8 |
| Storage | Postgres + pgvector |
| Evals | 53 cases in `evals/cases.json`, scored `exact_match` / `rule_based` / `manual_review`. No LLM-as-judge scorer exists. Only the 2 `groundedness` cases are wired into pytest (`test_groundedness_evals.py`); the rest are run manually |
| Observability | `/activity` page (shipped): per-request latency, tokens, cost, grounded flag, cached flag, plus expandable tool-call trace |
| Cost/token tracking | Computed in `app/observability/pricing.py`, stored in Postgres as `request_log.estimated_cost_usd`, read via `GET /observability/requests` |

### Scope

**Part 1 scope (historical)**: one working SQL path (refund-rate analysis)
and one working RAG path (refund policy lookup), proven end-to-end before
adding agents, security controls, or observability tooling.

**Current status beyond Part 1**: multimodal extraction (vendor invoices),
permission model v1 (header-based demo roles), tool-call tracing, and an
8-case prompt-injection eval category are all built. Multi-agent
decomposition is partially built: `investigation_planner.py` and
`data_analyst.py` implement a Planner → Data Analyst pipeline with tests
(DECISIONS.md #26), not yet wired to an endpoint. Model routing is still
not built.

**Still out of scope**: model routing, dedicated prompt-injection defenses
(the category is evaluated, not defended against as a feature), row-level
data isolation, real authentication.
