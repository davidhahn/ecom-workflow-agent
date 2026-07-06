## Architecture Decisions

### Repo shape: monorepo

Monorepo (`apps/web`, `apps/api`, `packages/shared`). Two repos rejected —
no organizational split to justify it (sole dev, no separate deploy
cadence). Shared types generated from FastAPI's OpenAPI spec via
openapi-typescript into `packages/shared`, imported by both apps. Without
codegen this decision is a wash; with it, monorepo wins on every axis.
Codegen is not optional — skipping it reintroduces the exact drift problem
two repos would have had, with less visibility.

### Orchestration seam: LLM proposes, Python enforces

Unchanged from prior system. Claude extracts intent via structured
tool-calling; a Python state machine owns all execution authorization.
LLM never executes directly.

The gate is now two mechanisms, not one:

1. **Structural gate** (deterministic) — SQL verb/table/column permission,
   refund threshold checks, approval routing. Unit-testable, binary pass/fail.
2. **Groundedness check** (probabilistic) — verifies RAG-sourced claims
   (e.g. refund policy interpretation) against the retrieved passage.
   Evaluated against a labeled set, not asserted true/false.

These are separate because they fail differently. A refund can pass every
structural check — correct amount, correct authorization tier, read-only
lookup — while resting on a misapplied or hallucinated policy clause. The
state machine cannot detect this; it has no visibility into meaning, only
structure. Treating groundedness as "one more rule in the same gate" was
considered and rejected — it would get implemented as a deterministic
check by default, which is the exact blind spot this split exists to avoid.

**Open**: PII column-scoping not yet decided — query-layer masking vs.
downstream handling. Structural gate currently checks verb + table only,
not column contents.

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | Python 3.14, FastAPI, uvicorn |
| Orchestration | Anthropic Python SDK (claude-sonnet-4-6) |
| Embeddings | `sentence-transformers` — BAAI/bge-m3 (local, air-gapped) |
| Storage | Postgres + pgvector (from Day 1 — SQL path requires it) |
| Evals | Custom harness: rule-based + LLM-as-judge |
| Observability | Reliability dashboard (in progress) |
| Cost/token tracking | Logged per-request in `data/eval_results/` (token count + estimated cost); dashboard surfacing in progress |

### Groundedness Check (not yet implemented)

### Scope
**Out of scope (deliberately) for Part 1:** multi-agent decomposition,
multimodal extraction, prompt-injection defense, model routing. Part 1
targets one working SQL path (refund-rate analysis) and one working RAG
path (refund policy lookup) over eCommerce operations data — not a broad
surface, but the two core paths proven end-to-end before adding agents,
security controls, or observability tooling.
