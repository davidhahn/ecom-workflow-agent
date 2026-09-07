# ecom-workflow-agent

An AI agent for e-commerce operations that answers data questions, retrieves policy, and evaluates refunds.

The model proposes what to do. Application code decides what's allowed to execute. A 79-case eval suite measures whether changes improve behavior.

Stack: Python, FastAPI, Claude, PostgreSQL/pgvector, SQLAlchemy, Next.js, Docker.

Around the model, I built execution controls, groundedness checks, evals, request tracing, and failure tests. Together they constrain what the agent can execute and make its failures explainable.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Case study](CASE_STUDY.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

![The agent refuses an ambiguous refund request because it can't reliably identify the customer, then the execution trace shows why and which controls ran, then the evaluation lab shows the suite that keeps this behavior measured.](docs/img/ambiguous-refusal-demo.gif)

The demo uses seeded data that resets daily, with scenarios covering data queries, policy retrieval, refunds, ambiguous customers, and prompt injection.

## Results

A 79-case eval suite scores every change against fixed cases. 18 of them are fully deterministic and run in CI on every push.

- **SQL correctness:** 57-71% → 100% across three runs. The eval caught two cases where structurally valid SQL returned the wrong number.
- **Policy retrieval:** 58% → 92%, after adding a relevance threshold so an off-topic question gets an honest "I don't know."

Full numbers and methodology: [full report](evals/primary_results.md) · [methodology](evals/methodology.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

## How it works

![Architecture diagram: a user request flows through the agent loop into the SQL tool or the RAG tool, through a deterministic enforcement seam, to a final response and request log.](docs/img/architecture-diagram.svg)

Claude gets two tools, one for SQL and one for policy retrieval, and chooses between them inside a capped loop. Every proposed action passes through deterministic execution and permission checks before it runs. Policy claims are checked against retrieved evidence, and every attempt is logged.

The refund evaluator works differently. Claude only extracts the fields, who's asking, what product, why. A fixed rule waterfall over real order rows makes the actual decision.

Full breakdown of each layer, file paths included: [ARCHITECTURE.md](ARCHITECTURE.md)

## What the evals found

The eval suite looked clean before it was checking the right thing. A query could pass every safety check and still compute the wrong answer, silently, because nothing compared the returned value against a real one. Fixing that measurement, not the model, is what closed the gap. The full story, including where else this happened, is in the [case study](CASE_STUDY.md).

## Limitations

- One specific phrasing still ranks the wrong policy chunk first under the production embedding model, and the relevance thresholds are calibrated against a small, hand-labeled sample.
- Eval categories run 2 to 12 cases each, enough to catch a regression. Accuracy at production scale would need a lot more.
- The judge that scores free-text answers has never been checked against a real failure, only against verdicts that already looked correct.
- Authentication is a header the caller sets themselves. Real auth is unbuilt.

## Run locally

Requires Python 3.14, Poetry, Node/pnpm, and Docker with pgvector.

```bash
docker compose up -d
cd apps/api && poetry install && poetry run alembic upgrade head && poetry run python -m app.db.seed
poetry run uvicorn app.main:app --reload --port 8000
```

Full setup, environment variables, and deploying to Render and Vercel: [docs/DEPLOY.md](docs/DEPLOY.md)

## More detail

- **[Case study](CASE_STUDY.md):** the investigation, measurements, and changes that came out of the eval work.
- **[Architecture](ARCHITECTURE.md):** the system design, enforcement boundaries, and tradeoffs.
- **[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab):** the live cases, results, and methodology.
- **[Deployment](docs/DEPLOY.md):** setup and deployment instructions.
