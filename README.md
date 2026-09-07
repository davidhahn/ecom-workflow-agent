# ecom-workflow-agent

An AI agent for e-commerce operations that interprets requests, retrieves structured data and policy context, and chooses the tools it needs to answer.

The model decides what should happen. Application code decides what's allowed to execute. That separation keeps a bad model decision from automatically becoming a bad action. A 79-case eval suite measures whether changes improve behavior.

**What I built around the model**

* **Execution controls** define what the agent can and cannot do.
* Every cited claim gets checked against retrieved or computed evidence, a **grounding check** run after the fact.
* **Evals** score each change against a fixed set of known cases.
* Every tool call, its latency, cost, and any failure gets written to a **request trace**.
* **Failure tests** deliberately break outputs and tool paths to see how the system behaves under stress.

**Stack:** Python, FastAPI, Claude, PostgreSQL/pgvector, SQLAlchemy, Next.js, Docker.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Case study](CASE_STUDY.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

![The agent refuses an ambiguous refund request because it can't reliably identify the customer, then the execution trace shows why and which controls ran, then the evaluation lab shows the suite that keeps this behavior measured.](docs/img/ambiguous-refusal-demo.gif)

The demo uses seeded data that resets daily, with scenarios covering data queries, policy retrieval, refunds, ambiguous customers, and prompt injection.

## Results

A 79-case eval suite scores every change against fixed cases. 18 are fully deterministic and run in CI on every push.

* **SQL correctness:** 57-71% → 100% across three runs. The eval caught two cases where structurally valid SQL returned the wrong number.
* **Policy retrieval:** 58% → 92%, after adding a relevance threshold so an off-topic question gets an honest "I don't know."

[Full report](evals/primary_results.md) · [Methodology](evals/methodology.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

## How it works

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

Claude gets two tools: one for SQL and one for policy retrieval. It chooses between them inside a capped loop. Every proposed action passes through deterministic execution and permission checks before it runs. Policy claims are checked against retrieved evidence, and every attempt is logged.

The refund evaluator uses a different boundary. Claude extracts the relevant fields: requester, product, and reason. A fixed rule waterfall over real order rows makes the actual decision.

This keeps the model useful for interpretation while leaving decisions that affect execution to code that can be tested directly.

Full breakdown of each layer, file paths included: [ARCHITECTURE.md](ARCHITECTURE.md)

## What the evals found

The first version of the eval suite looked clean until it checked the right thing.

A query could pass every safety check and still return the wrong answer because nothing compared the result against a known-correct value. The SQL was valid. The query was allowed to run. The system still produced the wrong result.

Adding that check exposed two failures that the original suite had missed. The model did not need to change. The measurement and enforcement layer did.

The same process exposed weaknesses in policy retrieval, free-text extraction, and failure handling. The full investigation is in the [case study](CASE_STUDY.md).

## Limitations

One specific phrasing ranks the wrong policy chunk first under the production embedding model. The relevance thresholds are calibrated against a small, hand-labeled sample.

Eval categories run 2 to 12 cases each. That is enough to catch regressions in the current implementation. It is not enough to establish production-scale accuracy.

The free-text judge has not been calibrated against known failures. Its current checks are based on verdicts that already looked correct.

Authentication is currently a caller-set header. Real authentication is unbuilt.

## Run locally

Requires Python 3.14, Poetry, Node/pnpm, and Docker with pgvector.

```bash
docker compose up -d

cd apps/api && poetry install && poetry run alembic upgrade head && poetry run python -m app.db.seed

poetry run uvicorn app.main:app --reload --port 8000
```

Full setup, environment variables, and deployment to Render and Vercel: [docs/DEPLOY.md](docs/DEPLOY.md)

## More detail

* **[Case study](CASE_STUDY.md)** — the investigation, measurements, and changes that came out of the eval work.
* **[Architecture](ARCHITECTURE.md)** — the system design, enforcement boundaries, and tradeoffs.
* **[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)** — the live cases, results, and methodology.
* **[Deployment](docs/DEPLOY.md)** — setup and deployment instructions.
