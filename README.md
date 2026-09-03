# ecom-workflow-agent

This is an operations assistant for an e-commerce business. Support staff and managers ask it questions in plain language: how the refund rate moved last month, what the policy says about a damaged shipment, whether a specific refund should go through. It answers by querying the orders database, searching the policy documents, or applying the refund rules, and it refuses when it can't identify the customer it's being asked about.

I built it around one question: what happens when the model gets something wrong, and how would you know? The model here only proposes an action. Code outside the model decides what's allowed to run. A separate check compares every claim in an answer against the evidence it came from. An eval suite scores every change against the same fixed cases, and I've broken the live system on purpose more than once to see what that suite couldn't catch.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Case study](CASE_STUDY.md) · [Evals & defects found](EVALS.md) · [Architecture decisions](ARCHITECTURE.md) · [Setup](docs/DEPLOY.md)

![The agent refuses an ambiguous refund request because it can't reliably identify the customer, then the execution trace shows why and which controls ran, then the evaluation lab shows the suite that keeps this behavior measured.](docs/img/ambiguous-refusal-demo.gif)

The demo runs on seeded data that resets daily. Curated scenarios cover a data question, a policy lookup, a refund decision, a customer the system can't identify, and an injection attempt where a fake instruction rides along inside the request text.

## How it works

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

> The model proposes what to do. Separate code decides whether it's allowed to run.

Claude sits behind two tools: one turns a question into SQL, one searches the policy documents. The orchestrator hands Claude both on every request and lets it pick, and caps the loop so a stuck question comes back honest and incomplete.

A generated SQL query clears three checks before it touches the database: an allowlist for tables and columns, a cost estimate, and a restricted database role that holds even if the first two have a bug. Every attempt gets logged, blocked or not.

Retrieval drops any policy chunk below a relevance threshold, so an off-topic question gets an honest "I don't know."

The refund evaluator turns a free-text request into an approve or deny decision through a fixed rule waterfall over real order rows. Claude only extracts the fields. It never decides the outcome.

A groundedness check runs after an answer comes back and confirms that any policy rule it cites showed up in what got retrieved for that request.

A permission gate checks the caller's role before a request reaches a tool, on the SQL, policy, ticket, and invoice endpoints. The combined analyze and refund endpoints only call read-only tools internally, so there's nothing on those two paths yet for the gate to block.

Every request to any of the four endpoints writes its own log line: the tools it called, what the guardrails did, latency, cost, and how it ended.

A 79-case eval suite scores changes against fixed expected answers. 18 of those cases are fully deterministic and run in CI on every push.

[See the full breakdown of what's enforced and why →](https://ecom-workflow-agent-web.vercel.app/architecture)

## What I measured

| What was measured | Cases | Runs per side | Before | After |
|---|---|---|---|---|
| Generated SQL returns the right number | 7 | 3 | 14/21 correct, 57-71% range | 21/21, stable |
| Policy retrieval finds the passage, or admits it can't | 12 | 3 | 7/12 | 11/12 |
| A combined data-and-policy answer, judged correct | 8 | 1 | 7/8 | 7/8, a different case failing |

The SQL row is 7 cases run 3 times each side, 21 attempts total. That's a small sample, but a jump from a 57-71% range up to a flat 100% across 21 tries is too large to be noise.

The retrieval row held steady across all 3 runs on both sides. That's why the gap still open after the fix counts as a real limitation, covered below.

The combined-answer row kept the same pass rate on both sides, and the failing case changed underneath it. The original failure was a refund-approval request that never said outright the system couldn't approve anything. That's fixed now. A different case took its place: an answer that disputed a real 236-day gap it should have confirmed against the database. Both sides come from a single run. Neither has been repeated yet.

The refund evaluator scores 12 for 12 on both sides. Nothing in its decision path calls a model, so a steady 12/12 is expected every time. It's a regression check.

Three more categories, groundedness, topic coverage, and resilience, are two-case regression checks with nothing to compare against yet. Three others, permission, prompt injection, and request faithfulness, don't have a baseline either. Every one of them shows up in the full report.

[Full report](evals/primary_results.md) · [Methodology](evals/methodology.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

**Three things the evals found:**

Two cases generated SQL that cleared every structural check and still returned the wrong number. One counted order lines where it should have counted units sold. The other counted refunds that were never approved. The harness only checked a query's shape until then, so the bug stayed hidden. Once it started checking the actual returned value, the first measurement came back at 66.7% semantic accuracy. A prompt fix brought that to 100%, holding across three runs.

Without a relevance threshold, retrieval always returned its closest chunks whether they were on-topic or not. Every off-topic question in the ablation set got a confident answer, never "I don't know." A threshold fixed most of that, but it doesn't travel between embedding providers. The same query, "damaged shipments policy," ranked the correct chunk 2nd locally and 4th under the production provider, outside any threshold that still made sense. Production now runs its own calibrated threshold, and that exact phrasing still ranks the wrong chunk first there.

Free-text extraction folded a quantity into a product name. "2 Ergonomic Desk Chairs" came back as the product name itself, and it never matched the real seeded product, "Ergonomic Desk Chair." The refund eval cases feed pre-extracted fields straight into the rule engine and skip extraction entirely, so nothing in the suite could have caught this. A real question against the live deployed system surfaced it.

The eval bug that started the whole error-analysis pass, and the judge calibration numbers behind the suite, are in the [case study](CASE_STUDY.md).

## Design decisions

**Claude proposes, Python decides.** Claude never runs a query or approves a refund directly. It proposes one, and a Python layer decides whether it's allowed. That layer is two checks. One is deterministic: is this table allowed, does this role have write access. The other reads meaning: does this specific claim in the answer match what got retrieved. Folding both into one deterministic gate would turn it into a simple pass or fail, and a refund can clear every structural check, the right amount, the right role, and still rest on a misread policy clause. Catching that needs a check built to look at meaning.

**A silent Postgres no-op.** A column-level REVOKE on `customers.email` looked like it worked. It ran clean, no error. I only found the problem by querying the role directly with `psql`: a table-wide GRANT and a column-level REVOKE are separate ACL entries in Postgres, and the REVOKE loses. The role could still read the column it was supposed to lose access to. The fix grants access to an explicit list of columns the role can see. Each new column added to the schema needs a matching update to that list by hand, a real cost, but a silent failure in the other direction would have let a customer's email through a query the app never flagged.

**Evaluation as the actual work.** Eval cases split two ways. Some score against a fixed expected value with no model call involved. Others need a person or a judge model to read free text and grade it. That split decides what runs in CI and what I run by hand. SQL correctness looks like a clean pass or fail, but the SQL itself comes from a live model call, so a perfect scorer still can't make the whole check deterministic. The refund evaluator has zero model calls anywhere in its decision, so it runs in CI without an API key. Running all 79 cases on every push isn't practical: half of them need a live model call to score meaningfully, and that would make CI flaky and gate every merge on a key. 18 run automatically. The rest I run by hand.

**Choosing a model by measurement.** Before picking Sonnet as the production model, I ran the full suite against Sonnet and a cheaper Haiku model: same prompts, same questions, same judge, three runs each. The aggregate score made Haiku look worse across the board. The category breakdown told a sharper story: real gaps on SQL generation and one compliance case, and one case where Haiku held up better. I kept Sonnet, weighing the categories carrying real financial and compliance risk more heavily than the aggregate number. That same breakdown caught a real gap in Sonnet's own answers too, one the aggregate score had been hiding as a strength. A one-sentence prompt fix closed it. Sonnet now leads on every case in the comparison.

## Limitations

- **Retrieval ranking.** One query, "damaged shipments policy," still ranks the wrong policy chunk first under the production embedding provider. Widening retrieval depth was tried as a fix and made things worse, letting off-topic content through. Closing this needs recalibration against production's actual embedding space, or a rerank step.
- **Threshold calibration.** The two relevance thresholds come from 18 labeled questions over a 21-chunk corpus, the entire real corpus that exists today. That's a small sample, and it's also the ceiling on how far these exact numbers can be trusted as the corpus grows or the embedding model changes.
- **Evaluation size.** Categories run 2 to 12 cases each, sized for a portfolio project. A percentage at this scale answers one question: did a change help or hurt. It doesn't support a claim about accuracy at production scale.
- **Judge error.** The judge's calibration check found zero disagreements against 33 audited verdicts, and every one of those landed on a pass-shaped outcome. No fail verdict has been checked against a human read yet, so I don't know the judge's error rate on catching a real failure.
- **Authentication.** Every request carries a role through a plain header, picked by whoever's calling. That's enough to test the permission gate's real logic, the read/write split between roles. A real deployment needs an actual identity provider before it touches a real customer's data.

## What I'd build next

1. **Record which model and prompt version answered each request.** That information only lives in eval run metadata today. It never reaches the live request log, so a real production question can't be traced back to what produced it.
2. **Close the remaining RAG ranking gap.** "Damaged shipments policy" still ranks the wrong passage first under the production embedding model. It's the sharpest concrete accuracy gap sitting in production right now.
3. **Mock the Anthropic client in the permission tests.** `pytest` still needs a real API key to pass, because a few tests exercise live endpoints to confirm role checks. The fix is known and just hasn't happened yet.

A longer list of bigger extensions, and the reason each one is still waiting, is in [LATER.md](LATER.md).

## Run locally

Needs Python 3.14 with Poetry, Node with pnpm, and Docker for Postgres with pgvector.

```bash
docker compose up -d
cd apps/api && poetry install && poetry run alembic upgrade head && poetry run python -m app.db.seed
poetry run uvicorn app.main:app --reload --port 8000
```

Full setup, environment variables, and deploying to Render and Vercel: [docs/DEPLOY.md](docs/DEPLOY.md).

## Deeper documentation

- **[Case study](CASE_STUDY.md):** the full story behind this project, the measurement work that reordered the roadmap, and what changed because of it.
- **[Architecture decisions](ARCHITECTURE.md):** the reasoning behind the design, with the tradeoffs and open questions attached to each choice.
- **[apps/api/README.md](apps/api/README.md):** the SQL path, RAG path, orchestrator, and observability layer, endpoint by endpoint, with file paths.
- **[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab):** every number in this file, live, with the methodology and caveats that decide what each one means.
- **[DECISIONS.md](DECISIONS.md):** the full decision log behind the project, entry by entry, including the ones that never made it into this file.
- **[Adversarial architecture review](ARCHITECTURE_CRITIQUE.md):** a critical review of the system's design, and what happened to each finding since.
- **[UI specification](docs/ui-spec.md):** who each screen is built for and what job it does.
- **[LATER.md](LATER.md):** bigger extensions past the near-term list above, each with the reason it's waiting.
- **[Blog series](https://blog.davidhahn.co/):** longer writing on the individual problems that came up along the way.
