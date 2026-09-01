# ecom-workflow-agent

This operations agent for an eCommerce business exists to answer one question: what happens when the model gets something wrong, and how would you know? The model interprets the request, and deterministic code decides what's allowed to execute. A separate check flags whether the model's claims hold up against what it retrieved or computed. I run it against an eval suite built from known answers, and I've broken the live system on purpose more than once, just to watch how it fails.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Evals & defects found](EVALS.md) · [Architecture decisions](ARCHITECTURE.md) · [Full decision log](DECISIONS.md) · [Setup & deployment](docs/DEPLOY.md) · [Blog series](https://blog.davidhahn.co/)

## 2. Architecture

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

> The LLM interprets requests and proposes actions. Deterministic layers independently enforce SQL safety, permissions, refund policy, approval boundaries, and auditing.

[See the full breakdown of what's enforced and why →](https://ecom-workflow-agent-web.vercel.app/architecture)

## 3. Measured results

| evaluation | baseline | current | n | result |
|---|---|---|---|---|
| SQL / SQL semantic | 14/21 (67%) | 21/21 (100%) | 7 | +33pp |
| RAG (policy retrieval) | 7/12 (58%) | 11/12 (92%) | 12 | +33pp |
| Mixed workflow | 7/8 (88%) | 7/8 (88%) | 8 | 0pp, different failing case |
| Refund evaluator | 12/12 (100%) | 12/12 (100%) | 12 | 0pp, deterministic |

- **SQL / SQL semantic** ran 3 times per side. Individual baseline runs ranged from 57% to 71%.
- **RAG** numbers come from the local embedding model. Production runs a different provider, with its own relevance threshold, and I haven't rerun this number against it yet.
- **Mixed workflow** held the same pass rate on both sides, and the failing case changed underneath it. The original failure was a refund-approval request whose answer never said the system couldn't approve anything. That's fixed now, and a different failure took its place: the judge caught an answer that disputed a real 236-day gap it should have confirmed against the database. It's a single run on each side, not repeated yet.

Two-case regression checks sit outside this table: `groundedness`, `topic_coverage`, `resilience`. Three more categories, `permission`, `prompt_injection`, `request_faithfulness`, don't have a baseline yet, so they're left out too. Both groups show up in the full report below. Two cases aren't enough for a percentage to mean much, and a number needs a baseline before it can become a delta.

[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab) · [Committed evaluation report](evals/primary_results.md) · [Evaluation methodology](evals/methodology.md)

## 4. Live demo

The demo runs on seeded fixture data that resets daily at 06:00 UTC.

**[Open the live demo →](https://ecom-workflow-agent-web.vercel.app/)**

<!-- TODO: record a 20-30s GIF: run a scenario, watch the badges, click into the trace -->

> Start with the curated scenarios. Each states the expected behavior before execution and links the result to its full trace.

### Data Analysis

> Ask a business question that requires generated SQL constrained by deterministic safety layers.

### Policy Retrieval

> Answer a policy question using retrieved evidence and an explicit relevance threshold.

### Refund Decision

> Resolve a seeded refund through deterministic policy logic rather than model judgment.

### Ambiguous Request

> Refuse when the customer cannot be identified reliably instead of guessing.

### Injection Attempt

> Show how deterministic controls contain an adversarial instruction even when the model is part of the workflow.

## 5. What makes this interesting

### 1. LLM Proposes, Deterministic Systems Enforce

> Claude proposes what to do next. Nothing takes effect until separate code checks it, whether that's a SQL query or a refund decision.

### 2. Database Permissions as a Real Safety Boundary

> A column-level `REVOKE` looked like it blocked the `email` column. In Postgres, that's a silent no-op next to a table-wide `GRANT`, and I only caught it by querying the role directly with `psql`.

### 3. Evaluation-Driven Development

> Every change ran through the same harness before it stuck. Sonnet's edge over a cheaper model only showed up in the per-category breakdown, real gaps the aggregate score alone would have hidden.

### 4. Failure Analysis and Ablation

> Widening the RAG retrieval depth looked like an easy fix for a missed case. Testing it showed it let more off-topic content leak through, with no gain on the on-topic side, so it got rejected and stayed out of the shipped system.

### 5. Execution as Evidence

> Every request writes its own record: tool calls, guardrail outcomes, latency, tokens, cost, retries, final status. The Activity page renders that record directly, so a claim about what happened doesn't have to rely on the answer's own wording.

## 6. Evaluation methodology

- **Versioned case suite:** pinned to a case set and a dataset version, a hash of `cases.json`. A `current` number always points to the same cases, no matter when someone reads it.
- **Deterministic scoring wherever possible:** most categories score with `exact_match` or `rule_based` checks against a fixed expected value, no model call inside the scoring itself.
- **A judge only for semantic criteria:** three categories need one, `mixed`, `prompt_injection`, `request_faithfulness`. Each asks the judge to read free text and decide whether it meets a described standard.
- **Human audit of every judged label:** the calibration sample found zero disagreements across 33 audited verdicts. Every one of those landed on a pass-shaped outcome, and no `fail` verdict has been checked against a human read yet.
- **Repeated model-backed runs:** SQL generation and the judged answers built on it vary run to run, and a single pass wouldn't show that. Each model-backed category ran 3 times. `mixed`'s current number above is the one exception. It comes from a single live run, not yet repeated ([`DECISIONS.md` #46](DECISIONS.md)).
- **Failure taxonomy:** every failure gets traced to a root cause before it's counted. That distinction separated a flawed test case, `sql-05`, from a real bug, `mixed-08`.
- **Frozen-suite comparison discipline:** a baseline-to-current delta only runs against the same case set. A number from an older suite gets labeled historical, so nobody mistakes it for one with the same denominator.
- **Production verification:** a passing suite and a working deployment are two different claims. Two real bugs only turned up by testing the live app directly. The suite alone never surfaced them.

> Deterministic regression checks run in CI. Model-backed evaluations remain offline because their outputs can vary and require interpretation.

Full suite, live model calls:

```
cd apps/api
EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --bypass-cache
```

Deterministic subset only, the one CI runs on every push, no API key needed:

```
cd apps/api
poetry run python ../../evals/run.py --subset deterministic
```

[Evaluation Lab →](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

## 7. Key design decisions

### Claude proposes, Python decides

Claude never executes anything directly. It only proposes a query or a tool call, and a Python layer decides whether that proposal gets to run. That layer is two independent checks: one deterministic (is this table allowed, does this role have write access), and one heuristic (does this specific claim in the answer match what got retrieved).

Folding groundedness into that same deterministic gate, as one more rule, would turn it into a simple pass or fail check. That's the blind spot the split is built to avoid. A refund can pass every structural check, the right amount, the right role, and still rest on a misread or invented policy clause. Catching that takes a check that looks at meaning, which the structural gate was never built to do.

### Evaluation as a real deliverable

Eval cases split into two kinds. Deterministic ones get scored against a fixed expected value, with no live model call. Model-dependent ones need a human or a judge model to grade a free-text answer. That split decides what can run automatically in CI, and what has to be run by hand.

SQL correctness looks like it should be a clean pass or fail, but the SQL itself comes from a live model call. Even a perfect deterministic scorer can't make the whole check deterministic when a nondeterministic model produced the thing being scored. Refund evaluation works differently, with zero LLM calls anywhere in its decision path, so it can run in CI without an API key at all.

Running the full 79-case suite on every push isn't practical. Half those cases need a live model call to score meaningfully, which would make CI flaky and gate every merge on an API key. So 18 of the 79, the fully deterministic ones, run automatically on every push. The rest run by hand.

### Choosing a model by measurement

Before settling on Claude Sonnet as the production model, I ran the full eval suite against both Sonnet and a cheaper Haiku model, using the same prompts, the same cache-bypassed questions, and the same judge, three runs apiece.

The aggregate score made Haiku look uniformly worse. The per-category breakdown told a sharper story: real gaps in SQL generation and one compliance case, plus one case where Haiku was more reliable than Sonnet. I kept Sonnet, weighing the categories that carry real financial and compliance risk more heavily than the aggregate number. That same per-category read caught a real, fixable prompt gap in Sonnet's own answers, one the aggregate score alone would have hidden as a strength. A one-sentence prompt fix closed that gap later ([`DECISIONS.md` #46](DECISIONS.md)). Sonnet now leads on every case in the comparison.

## 8. Component deep dives

### Orchestrator: `app/orchestrator/analyze_service.py`

This combines the SQL and RAG paths behind one endpoint. Claude gets both tools on every call and picks freely, both, one, or neither, and the loop is capped at a fixed number of rounds, so a model that can't converge returns an honest "incomplete" response instead of stalling or guessing.

A real bug here shows why this needs testing. A request asking the agent to "approve this refund" got back an answer that looked up the refund, found it already approved in the seed data, and said "no further action needed," without ever stating outright that it had no ability to approve anything. The system prompt listed the two tools and what each did, but it never said the words: neither one could write.

One added sentence fixed it. The fix held up 3 out of 3 on the exact case that had been failing, with no regression across 19 other cases sharing the same prompt. In the transcript, this read as a slightly too-helpful answer, easy to miss without an eval case built specifically to catch it.

### SQL path: `app/query/claude_client.py`, `app/query/validation.py`

This turns a question into a SQL query, then checks it's safe to run before it touches the real database, in three independent layers. An AST-level check allowlists tables, columns, and functions, which is what blocks `customers.email` from ever being selected. A cost gate rejects a syntactically valid query that would be too expensive, checked against Postgres's own `EXPLAIN` estimate before running.

A separate, restricted database role is the backstop. Even if the first two layers had a bug, the database itself won't grant access beyond what that role allows.

Three layers is more to build and reason about than one, but a prompt instruction like "never select the email column" is a request the model can ignore or get wrong. Only a check outside the model's control turns it into a guarantee.

### RAG path: `app/rag/service.py`, `app/rag/embeddings.py`, `app/rag/ingest.py`

This retrieves the policy passages relevant to a question, and refuses to answer when nothing relevant comes back. It compares chunks to the question by similarity, and drops anything that doesn't clear a calibrated distance threshold. There's no fixed top-k fallback, so an off-topic question just gets "I don't know."

The threshold turned out not to be portable. Local development uses a free local embedding model, but production uses a different, hosted one, because the local model's memory footprint alone was too much for the deploy environment. The similarity threshold calibrated for one doesn't transfer to the other. A real production question surfaced this directly, and the threshold had to be recalibrated per provider. One retrieval gap from that investigation is still open, and stays documented as a known limitation.

### Semantic correctness layer: `app/orchestrator/groundedness.py`, `app/orchestrator/topic_coverage.py`

This catches what structural checks can't see: an answer that's syntactically fine and permission-compliant, but wrong or fabricated underneath. The groundedness check confirms that a policy rule the final answer cites appeared among what the system retrieved for that request, matching on both rule number and title, since a citation doesn't need a number to still be one. The topic coverage check catches something different: an answer stating a fact about something the system has no data for at all, like shipment tracking, the recurring example.

This works by matching titles, so it can occasionally flag a phrase that wasn't meant as a citation. That trade is accepted on purpose. A false alarm only costs a warning banner, while a real hallucination marked "trustworthy" costs the user's trust in the whole system. Over-flagging is the safer failure of the two.

### Refund evaluator: `app/orchestrator/refund_evaluator.py`, `app/orchestrator/refund_extraction.py`

This turns a free-text refund request into an approve or deny decision with a specific policy rule cited, and it has zero ability to write to the refunds table. Claude only extracts fields from the free text, who's asking, what product, why, and never decides the outcome. The decision itself, approve, deny, needs manager approval, or refuse to guess, comes from a fixed rule waterfall over real order rows, with no model call anywhere in that step.

If the customer or product can't be matched confidently to a real order, the system refuses to guess rather than picking the closest match. That can be frustrating in an edge case. A wrong-customer match on a refund decision is a worse failure than an honest "couldn't process this."

### Permission gate: `app/permissions.py`

This controls which role can call which tool, checked before a request reaches the tool at all. Every tool is tagged read-only or write, and every defined role gets at least read-only access, which means the gate's real job is the read/write split: a support agent can draft a ticket, but only a manager or admin can confirm one and commit it.

This only fronts the single-tool endpoints (direct SQL, direct policy search, tickets, invoices). The combined analyze and refund endpoints don't have it wrapped around them, because every tool they call internally is already read-only-tier and open to every role by default. There's currently nothing on those two paths for the gate to block.

### Investigation pipeline: `app/orchestrator/investigation_planner.py`, `app/orchestrator/data_analyst.py`

This is a two-stage pipeline for open-ended questions like "why did revenue drop last week." A Planner proposes which signals to check, SQL, RAG, or both. A Data Analyst runs them, with one failing signal isolated so it doesn't take the others down. It's real, tested code, callable directly, but it isn't wired to any API endpoint, and it's missing the stage that would turn gathered evidence into a written answer.

Finishing it means more than one more Claude call. It means new eval cases, a groundedness check for whatever that stage writes, and a real place for it in the demo, all new surface area I kept out of scope while I was still measuring the rest of the system.

### Eval harness: `evals/run.py`

This is what makes every claim above checkable instead of asserted. There are 79 cases across 13 categories, 18 of them deterministic, scored against a fixed expected answer with no live model call. The rest are model-dependent, needing a human or a judge model to grade. The deterministic 18 run automatically on every push to main, and the rest run by hand, since scoring them meaningfully needs a live API call.

A deterministic scorer doesn't mean a deterministic system. SQL cases have a deterministic scorer, but the SQL itself still comes from a live, nondeterministic model call, which is why SQL cases can't run unattended in CI, even with a perfect scorer.

## 9. What the evaluations found

### Evaluation Bug

`sql-05` looked like a real failure: the agent was asked to write, and it returned an unrelated read instead. The case was checking two different things at once, whether Claude tried to write and whether the safety layer would have blocked it, so a failure couldn't say which one broke. A direct test of the safety layer replaced it, and that one has passed every run since.

### Semantic SQL Gap

Two cases generated SQL that passed every structural check and still returned the wrong number. `sql-01` counted order lines where it should have counted units sold, and `sql-semantic-01` also counted refunds that were never approved. For a while, the harness only checked a query's shape, so the bug stayed hidden. Once it started checking the actual returned value against a hand-verified number, the first measurement came back at 66.7% semantic accuracy. A targeted prompt fix brought that to 100%, holding across three runs since.

### Retrieval Relevance

Retrieval always returned its closest chunks, on-topic or not. All 5 off-topic questions in the ablation set, run 3 times each, got a confident-sounding answer every time, never `I don't know`. Adding a relevance threshold, below which nothing counts as evidence, brought that to 12 of those 15 runs.

### Environment Skew

The same query, `"damaged shipments policy"`, ranked the correct policy chunk 2nd locally, comfortably inside the 0.46 relevance cutoff. Under the production embedding provider, the identical query and corpus ranked that chunk 4th, outside any threshold that would still make sense. Swapping only the embedding provider was enough to turn a real production question into a false `I don't know`, and it's why the threshold now has separate values for local and production.

### Groundedness Calibration

Twenty real and constructed examples got a human label, grounded or not, then a check against what the groundedness heuristic actually flagged. Of 4 real fabrications in the set, it caught 2 and missed 2. Of 16 genuinely grounded answers, it flagged 5 as problems anyway, the over-flagging bias `DECISIONS.md` already calls out on purpose. One of the 2 misses stood out: an answer cited a real, retrieved rule number, then attached a claim the retrieved text never made. The heuristic checks whether a number was retrieved. It has no way yet to check whether the words after it are true.

### Extraction Blind Spot

Free-text extraction folded a stated quantity into the product name. "2 Ergonomic Desk Chairs" came back as the product name itself, and that string never matched the real seeded product, "Ergonomic Desk Chair." The refund eval cases feed pre-extracted fields straight into the rule engine, skipping extraction entirely, so no case in the suite could ever have caught this. A real question against the live, deployed system surfaced it directly.

## 10. Production readiness

> Production readiness means deliberately exercising the failure and environment boundaries, not merely deploying successfully once.

### CI Regression Gate

The deterministic subset of the eval suite runs in CI on every push, no live model call needed. I tested the gate itself by moving the refund approval threshold by 10x on a throwaway branch, then watching the real workflow run. The build failed, catching the change before it could reach main.

### Independent CI Checks

> CI steps were structured so an earlier failure could not silently prevent independent checks from reporting their own results.

In this repo, that's `pytest` and the deterministic eval subset, two steps in the same CI job. The eval step runs with `if: ${{ !cancelled() }}`, so a `pytest` failure upstream can't quietly skip it. The first time I broke a threshold on purpose, a `pytest` policy check caught it, and GitHub Actions' default behavior, skip everything after a failed step, kept the eval step from running at all. Fixing that ordering, then breaking the same threshold again, confirmed both steps now report on their own.

### Bounded External Failures

Anthropic calls on the SQL and analyze paths get a 30-second timeout and one bounded retry, a flat 2-second delay, and only for timeouts, dropped connections, rate limits, and 5xx responses. Anything else fails right away. When both attempts fail, each path returns its own structured failure instead of raising: `SqlQueryResponse(status="error")` or `AnalyzeResponse(incomplete=True)`. A `retry_count` column on `request_log` records which one happened, tested by mocking a failure twice on purpose.

### Production Verification

The same class of question behind the curated scenarios also gets asked directly against the live, deployed app, not just replayed through the offline suite. That's how two of the findings above surfaced at all: the RAG threshold gap and the extraction blind spot both passed the local suite clean and only broke against production.

### Environment Parity

> Retrieval thresholds and behavior were verified against the production provider because local evaluation alone did not predict production ranking exactly.

Local development runs a free embedding model at a 0.46 relevance threshold. Production runs a different, hosted provider at 0.48. The same query can rank a real policy chunk 2nd under one and 4th under the other, so the threshold gets calibrated and verified separately for each provider.

## 11. Limitations

### Retrieval Ranking

One query, "damaged shipments policy," still ranks the wrong policy chunk first under the production embedding provider. Local development and production run different embedding models, and the relevance ranking that holds under one doesn't hold under the other. Widening retrieval depth was tested as a fix, and it made things worse, letting off-topic content through. Closing this gap means recalibrating or reranking specifically against production's embedding space. The suite's default local runs won't surface it.

### Threshold Calibration

The 0.46 and 0.48 relevance thresholds come from calibrating against 18 labeled questions over a 21-chunk policy corpus, the entire real corpus that exists today. That sample size is what surfaced the local-versus-production gap in the first place, and it's also the ceiling on how far these exact numbers can be trusted as the corpus or embedding model changes. Adding real policy documents, or swapping the embedding model again, calls for a fresh calibration pass against a labeled sample built for whatever's new.

### Evaluation Size

Categories in the eval suite run 2 to 12 cases each, sized for a portfolio project, not a production accuracy study. A percentage at this scale answers one question: did a change make things better or worse. It doesn't support a claim about how the system performs across the wider range of questions a real deployment would see. Trusting a category's number at production scale means growing it well past a dozen cases first, with real question variety behind each one.

### Judge Error

The judge's calibration check found zero disagreements against 33 human-audited verdicts, and every one of those verdicts landed on a pass-shaped outcome. No `fail` verdict has been checked against a human read yet, so the judge's error rate on catching a real failure is still unmeasured. The same model that answers a question also grades the answer, a real bias risk nobody has tested for. Closing this gap needs a labeled sample of real failures and, ideally, a different model doing the grading, so the same architecture isn't both taking the test and scoring it.

### Authentication

Every request carries a role through a plain header, `read_only_viewer`, `support_agent`, `manager`, or `admin`, picked by whoever's calling. That's enough to test the permission gate's real logic, the read/write split between roles, without building a login system the gate itself doesn't depend on. Handling a real user's data or a real refund means replacing that header with an actual identity provider and session handling first.

### Seeded Domain

The system runs against one seeded schema: a fixed set of customers, orders, refunds, and a 21-chunk policy corpus that resets daily. The SQL allowlist, the blocked-column list, and the RAG index are all hand-built for this exact schema. Pointing this at a different company's real tables and policy documents means rebuilding those three by hand again, or replacing them with something that can learn a new schema on its own.

## 12. Local setup

Deployment steps for Render and Vercel live in [docs/DEPLOY.md](docs/DEPLOY.md). This section covers running the project locally.

### Prerequisites

- Python 3.14 (`apps/api/pyproject.toml` pins `>=3.14,<4.0`)
- [Poetry](https://python-poetry.org/), for the API's dependencies
- Node.js and [pnpm](https://pnpm.io/) (pinned to `10.25.0` in `package.json`), for the web app and the generated shared types
- Docker, for Postgres with pgvector

### Environment variables

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

`apps/api/.env` needs `ANTHROPIC_API_KEY`, `OPS_AGENT_DB_PASSWORD`, `REFUND_EVALUATOR_DB_PASSWORD`, and `INTERNAL_PROXY_SECRET`. `EMBEDDING_PROVIDER` defaults to `local` and needs no key. Set it to `voyage` with a `VOYAGE_API_KEY` to match what production runs instead.

`apps/web/.env` needs the same `INTERNAL_PROXY_SECRET` value, byte-for-byte, plus `NEXT_PUBLIC_API_URL` pointing at the local API.

### Database startup

```bash
docker compose up -d
```

Brings up a single `postgres` service (`pgvector/pgvector:pg17`) on `localhost:5432`.

### Migration

```bash
cd apps/api
poetry run alembic upgrade head
```

### Seed

```bash
poetry run python -m app.db.seed
poetry run python -m app.rag.ingest
```

`seed.py` truncates and reseeds all nine tables with deterministic fixture data, and it's safe to rerun. `rag.ingest` loads the policy corpus RAG retrieves against.

### API

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

Health check at `GET /health`, OpenAPI spec at `/openapi.json`. `apps/api/README.md` documents the full route surface.

### Web app

```bash
pnpm install
pnpm --filter web dev
```

### Tests

```bash
cd apps/api
poetry run pytest
```

### Evaluations

```bash
cd apps/api
poetry run python ../../evals/run.py --subset deterministic
```

No API key needed. It's the same deterministic subset CI runs on every push. The full suite, with live model calls, needs `EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --bypass-cache` instead, covered in Evaluation methodology above.

## 13. What I'd build next

Ordered by where the evidence points.

1. **Record which model and prompt version answered each request.** That information only exists in eval run metadata today, not in the live request log, so a real production question can't be traced back to which model or prompt produced it. Everything else about a request already gets logged: latency, tokens, cost, grounded status. This is the one gap left in that story.
2. **Close the remaining RAG ranking gap.** One specific phrasing ("damaged shipments policy") still ranks the wrong passage first under the production embedding model. It's documented and still unresolved, the sharpest concrete accuracy gap sitting in production right now.
3. **Mock the Anthropic client in the permission tests.** `pytest` still needs a real API key to pass, because a few tests exercise live endpoints to confirm role checks. The fix is known and scoped. It just hasn't been done yet.
4. **Generalize PII column-scoping.** The code blocks only `customers.email` today, hardcoded as a single exclusion. Before any new table or column with sensitive data gets added, this needs a real, general policy.
5. **Finish the investigation pipeline's synthesis stage.** Deliberately last. It's real, tested code, short one stage, and it's the feature I'd most want to build for its own sake, which is why it's ranked behind four things with real evidence behind them.

A few things stay unbuilt on purpose. A reranker heads the list: the policy corpus holds 21 chunks, so there is nothing to rerank. Real authentication would prove nothing the header-based demo role doesn't already exercise. The ticket and invoice flows work through the API today, and adding screens for them repeats that proof without strengthening it. The Ask interface stays single-turn by design, so a follow-up question starts a new request.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind |
| Backend | Python 3.14, FastAPI |
| Orchestration | Anthropic Python SDK (claude-sonnet-4-6) |
| Storage / retrieval | Postgres + pgvector; BGE-M3 (local dev) / Voyage AI (deploy) |
| Evals | 79 cases across 13 categories; 18 run automatically via `evals/run.py` on every push, the rest run by hand |

Deploying to Render and Vercel: [docs/DEPLOY.md](docs/DEPLOY.md). API surface details: [`apps/api/README.md`](apps/api/README.md).

## 14. Deeper documentation

- **[Architecture decisions](ARCHITECTURE.md):** the load-bearing calls behind this project, written up as decisions with the tradeoffs and open questions attached to each one.
- **[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab):** every number in this README, live, with the methodology and the caveats that decide what each one means.
- **[DECISIONS.md](DECISIONS.md):** the full decision log behind the project, entry by entry, including the ones that never made it into this README.
- **[Adversarial architecture review](ARCHITECTURE_CRITIQUE.md):** a critical review of the system's design, and a record of what happened to each finding since.
- **[UI specification](docs/ui-spec.md):** who each screen is built for and what job it does, useful if the design choices need explaining before the screenshots do.
