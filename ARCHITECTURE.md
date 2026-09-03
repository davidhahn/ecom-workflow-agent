# Architecture

How this system works today: the request flow, the two gates that enforce it, each component, and how it's deployed. For why specific choices were made, see `DECISIONS.md`. For local setup, see `docs/DEPLOY.md`.

## Request flow

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

A request reaches the API as one of four kinds: a SQL question, a policy question, a refund evaluation, or a mixed request that needs more than one of those. For the mixed case, Claude gets both the SQL and RAG tools on every call and picks freely, both, one, or neither, inside a loop capped at four rounds. Every tool call it proposes routes through the same execution path a direct call to that tool would use, so a query proposed here doesn't get a second, unchecked path to the database.

Each proposal passes through the two gates below before it runs. The result, along with every tool call, guardrail outcome, and retry, gets written to `request_log` as one row, whether the request succeeded or not.

## The two gates

Claude extracts intent through structured tool calls. A Python layer owns every decision about what's allowed to execute, and the model never runs anything directly.

That layer is two separate mechanisms. A structural gate checks SQL verbs, tables, and columns against an allowlist, and routes refund decisions through fixed thresholds. It's deterministic and unit-testable: a query or a refund either clears the rules or it doesn't. A groundedness check runs after an answer comes back. It confirms that any policy rule number cited in the answer appeared among the chunks retrieved for that request, matching structurally on the rule's number and title, not by reading what the surrounding sentence claims.

The two exist separately because they fail in different ways. A refund can clear every structural check, the right amount, the right authorization tier, a read-only lookup, and still rest on a misapplied or invented policy clause. The structural gate has no way to catch that; it checks structure, never meaning. Folding groundedness into the same gate as one more rule would turn it into a simple pass or fail check. That's the blind spot the split exists to avoid.

## Components

**Orchestrator** (`app/orchestrator/analyze_service.py`) combines the SQL and RAG paths behind `/query/analyze`. Claude gets both tools on every call and picks freely, and the loop is capped at four rounds, so a model that can't converge returns an honest, incomplete response. The system prompt has to state the write boundary explicitly. An early version didn't, and Claude found an already-approved refund and reported "no further action needed" without ever declining the request outright. One added sentence fixed it.

**SQL path** (`app/query/validation.py`, `app/query/claude_client.py`, `app/query/audit.py`) turns a question into a query, then runs it through three independent safety layers before it touches the database. An AST check allowlists tables, columns, and functions, and blocks `customers.email` outright. A cost gate rejects anything too expensive, checked against Postgres's own `EXPLAIN` estimate. A restricted database role, `ops_agent_readonly`, is the backstop: even if the first two layers had a bug, the role itself can't read past what it's granted. Every attempt gets logged, blocked or not.

**RAG path** (`app/rag/service.py`, `app/rag/embeddings.py`, `app/rag/ingest.py`, `app/rag/chunking.py`) retrieves the policy passages relevant to a question and refuses to answer when nothing relevant comes back. Chunks are compared by similarity, and anything below a calibrated distance threshold gets dropped, with no fixed top-k fallback. The threshold isn't portable between embedding providers, covered under Data and deployment below.

**Refund evaluator** (`app/orchestrator/refund_evaluator.py`, `app/orchestrator/refund_extraction.py`) turns a free-text request into an approve or deny decision with a specific rule cited, and it has zero ability to write to the refunds table. Claude only extracts fields: who's asking, what product, why. The decision runs through a fixed rule waterfall over real order rows, first match wins: category exclusion, time window, evidence, repeat-refund flag, approval threshold, then approved. If the customer or product can't be matched confidently, the evaluator refuses to guess.

**Groundedness check** (`app/orchestrator/groundedness.py`, `app/orchestrator/topic_coverage.py`) is described above under The two gates. A second check, topic coverage, catches a related but different problem: an answer stating a fact about something the system has no data for at all, like shipment tracking. Both are deliberately biased toward over-flagging. A false alarm costs a warning banner. A hallucination marked trustworthy costs the user's trust in the whole system.

**Permission gate** (`app/permissions.py`) checks a caller's role against what a tool requires before the request reaches it, keyed by tool name against one shared registry, not by endpoint or a string match on the URL. It fronts the single-tool endpoints: SQL, policy search, tickets, invoices. The combined analyze and refund endpoints call only read-only-tier tools internally, open to every role by default, so there's nothing on those two paths yet for the gate to block.

**Request log** (`app/observability/`) writes exactly one row per call to any of the four main endpoints, success or failure, timed by a context manager that writes on exit no matter how the block exits. Field population is uneven on purpose: token counts and cost only get set where a Claude call happened, `grounded` only applies to analyze, a retry count only appears where a retry ran. The Activity page renders this table directly, so a claim about what happened doesn't have to rely on the answer's own wording.

## Data and deployment

The schema runs against nine seeded tables, customers, products, orders, order items, refunds, support tickets, shipments, web analytics, and campaigns, truncated and reinserted deterministically by `seed.py` so the same edge cases exist on every run. Production reseeds daily on a cron schedule, independent of deploys.

Two separate read-only Postgres roles enforce the boundary at the database itself. `ops_agent_readonly` blocks `customers.email`, since the SQL path's answers can end up quoting whatever it selects. `refund_evaluator_readonly` grants that same column, since the evaluator needs it to look a customer up, but it never writes email into a response, so the same risk doesn't apply.

Local development embeds policy text with a free local model, `BAAI/bge-m3`. Production calls a hosted provider, Voyage AI, because the local model's memory footprint didn't fit the deploy environment. That split is also why the RAG relevance threshold is calibrated separately per provider, covered in the README's limitations.

Render hosts the API, the database, and the daily reseed cron. Vercel hosts the frontend separately, behind a shared proxy secret and CORS as two independent perimeter layers. Full deployment steps: `docs/DEPLOY.md`.

## Status

Built and live: the SQL and RAG paths, the refund evaluator, the two gates above, permission enforcement, request tracing, and the vendor invoice and support ticket draft/confirm flows.

Partially built: an investigation pipeline, a Planner and a Data Analyst that gather evidence for open-ended questions like "why did revenue drop last week" (`DECISIONS.md` #26). It's tested directly against real seeded data but not wired to any endpoint, and it's missing the stage that would turn gathered evidence into a written answer.

Not built: model routing to a cheaper model for low-risk questions, a dedicated prompt-injection defense beyond what the two gates already catch, row-level data isolation, real authentication in place of the header-based demo role, and a general column-classification policy. Today that policy is one hardcoded exclusion, `customers.email`, enforced in `app/query/constants.py` and backed by the column-level grants described above. Nothing beyond that one column has ever been classified as sensitive.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | Python 3.14, FastAPI, uvicorn |
| Orchestration | Anthropic Python SDK (claude-sonnet-4-6) |
| Embeddings | `EMBEDDING_PROVIDER`-dispatched: local `sentence-transformers` BAAI/bge-m3 (dev default) or hosted Voyage AI `voyage-3.5-lite` at 1024 dims (deploy). See `DECISIONS.md` #8 |
| Storage | Postgres + pgvector |
| Evals | 79 cases in `evals/cases.json`, 18 fully deterministic and run in CI via `evals/run.py --subset deterministic`. `apps/api/tests/` (`poetry run pytest`) covers SQL safety, permissions, refund policy drift, and the groundedness and topic-coverage functions directly, independent of the eval suite |
| Observability | `/activity` page: per-request latency, tokens, cost, grounded flag, cached flag, plus an expandable tool-call trace |
| Cost/token tracking | Computed in `app/observability/pricing.py`, stored in Postgres as `request_log.estimated_cost_usd`, read via `GET /observability/requests` |
