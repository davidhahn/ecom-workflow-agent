# ecom-workflow-agent

This operations agent for an eCommerce business exists to answer one question: what happens when the model gets something wrong, and how would you know? The model interprets the request, and deterministic code decides what to do next, checking whether its claims hold up against what it retrieved or computed. I run it against an eval suite built from known answers, and I've broken the live system on purpose more than once, just to watch how it fails.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Evals & defects found](EVALS.md) · [Architecture decisions](ARCHITECTURE.md) · [Full decision log](DECISIONS.md) · [Setup & deployment](docs/DEPLOY.md) · [Blog series](https://blog.davidhahn.co/)

> The demo runs on seeded fixture data that resets daily at 06:00 UTC. The Scenario Demo on the landing page runs five curated requests end to end: SQL analysis, policy lookup, a refund approval, a refusal, and a prompt-injection attempt. Each one states the expected behavior first, then links to the real execution trace behind the result.

<!-- TODO: record a 20-30s GIF: run a scenario, watch the badges, click into the trace -->
![Demo](docs/demo.gif)

## 2. Architecture

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

> The LLM interprets requests and proposes actions. Deterministic layers independently enforce SQL safety, permissions, refund policy, approval boundaries, and auditing.

[See the full breakdown of what's enforced and why →](https://ecom-workflow-agent-web.vercel.app/architecture)

## 3. Key design decisions

### Claude proposes, Python decides

Claude never executes anything directly. It only proposes a query or a tool call, and a Python layer decides whether that proposal gets to run. That layer is two independent checks: one deterministic (is this table allowed, does this role have write access), and one heuristic (does this specific claim in the answer match what got retrieved).

Folding groundedness into that same deterministic gate, as one more rule, would turn it into a simple pass or fail check. That's the blind spot the split is built to avoid. A refund can pass every structural check, the right amount, the right role, and still rest on a misread or invented policy clause. Catching that takes a check that looks at meaning, which the structural gate was never built to do.

### Evaluation as a real deliverable

Eval cases split into two kinds. Deterministic ones get scored against a fixed expected value, with no live model call. Model-dependent ones need a human or a judge model to grade a free-text answer. That split decides what can run automatically in CI, and what has to be run by hand.

SQL correctness looks like it should be a clean pass or fail, but the SQL itself comes from a live model call. Even a perfect deterministic scorer can't make the whole check deterministic when a nondeterministic model produced the thing being scored. Refund evaluation works differently, with zero LLM calls anywhere in its decision path, so it can run in CI without an API key at all.

Running the full 79-case suite on every push isn't practical. Half those cases need a live model call to score meaningfully, which would make CI flaky and gate every merge on an API key. So 18 of the 79, the fully deterministic ones, run automatically on every push. The rest run by hand.

### Choosing a model by measurement

Before settling on Claude Sonnet as the production model, I ran the full eval suite against both Sonnet and a cheaper Haiku model, using the same prompts, the same cache-bypassed questions, and the same judge, three runs apiece.

The aggregate score made Haiku look uniformly worse. The per-category breakdown told a sharper story: real gaps in SQL generation and one compliance case, plus one case where Haiku was more reliable than Sonnet. I kept Sonnet, weighing the categories that carry real financial and compliance risk more heavily than the aggregate number. That same per-category read caught a real, fixable prompt gap in Sonnet's own answers, one the aggregate score alone would have hidden as a strength.

### A guardrail only proves itself once you've broken it on purpose

A green CI pipeline only proves today's code passes. It says nothing about whether the pipeline would catch a real bug. I deliberately introduced one on a throwaway branch, moving the refund approval threshold by 10x, then watched the real CI run to see what happened.

It failed, in a way I didn't expect. A pytest policy check caught it before the eval subset ever got a turn, even though the eval subset was the check built for this case, because one failing CI step was silently skipping the ones after it. I fixed the workflow so later steps still run after an earlier failure, then broke the same threshold a second time to confirm both checks now fire in the same run.

## 4. Component deep dives

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

## 5. Evaluation and results

Every path above gets checked against a fixed set of real questions with known-correct answers, and separately, against the deployed system itself. Both mattered, and they caught different bugs.

| Case | What it catches | The fix |
|---|---|---|
| [`ground-01-title-phrase-false-positive-rule-5`](evals/cases.json) | An answer describes rule 5 ("Wrong Item Shipped") by its title, in detail, without ever citing it by number, while the retrieval for that request surfaced rules 4 and 1, not 5. A numeric-only citation check would have missed this and reported a false groundedness failure. | Groundedness checking now matches on rule titles as well as numbers, derived from the same source the retrieval index uses, one source of truth to maintain. |

Two other findings came only from testing the live, deployed app directly:

- **The RAG relevance threshold didn't transfer between embedding models.** I calibrated it once, to 0.46, against the free local model used in dev, but production runs a hosted Voyage model instead. A real question, "What's our policy on damaged shipments?", got a false "I don't know" live, something that never showed up locally, since local eval runs default to the local model. Rerunning the same 18-question calibration under Voyage produced a per-provider threshold (0.46 local, 0.48 Voyage) and closed most of the gap. Widening the retrieval depth was also tested as a fix and rejected: it let off-topic content leak through without ever surfacing the missing passage. One case is still open, and stays documented as a known limitation.
- **Free-text extraction was folding a stated quantity into the product name.** "2 Ergonomic Desk Chairs" came out as the product name verbatim, and that never matched the real product, "Ergonomic Desk Chair," in the database. The eval suite's refund cases feed pre-extracted fields straight into the rule engine, skipping the extraction step entirely, so this bug was invisible to the suite by construction. It only showed up by asking the real, deployed system a real question.

A passing eval score proves the harness works. Whether the deployed system behaves the same way is a separate question. Two of the three fixes above came directly from testing the live app.

## 6. What I'd build next

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

Local setup, running the apps, and deploying to production: [docs/DEPLOY.md](docs/DEPLOY.md). API surface details: [`apps/api/README.md`](apps/api/README.md).
