# ecom-workflow-agent

This project focuses on the challenges that arise when an LLM starts working with real data, tools, and business rules.

**What the agent does**

The agent interprets e-commerce operations requests, retrieves structured data and policy context, and chooses the tools it needs to answer.

The model can decide what should happen, but application code decides what is allowed to execute. That separation keeps a bad model decision from automatically becoming a bad action.

**What I built around the model**

- **Execution controls** that define what the agent can and cannot do.
- **Grounding checks** that compare cited policy names and numbers with the passages retrieved for an answer.
- **Evals** that test each change against a fixed set of known cases.
- **Request traces** that record tool calls, latency, cost, and failures.
- **Failure tests** that deliberately break outputs and tool paths to show how the system behaves under stress.

**The broader goal**

The project is about designing a system that can catch, explain, and contain model errors. That pushed the work beyond prompting and into execution control, evaluation, observability, and failure handling.

**[Live demo](https://ecom-workflow-agent-web.vercel.app/)** · [Case study](CASE_STUDY.md) · [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)

## Results

I used a dataset of 79 evaluation cases to test behavior against known answers and expected outcomes. Eighteen cases run in CI without live model calls.

- **SQL correctness: 67% → 100%.** Seven cases ran three times before and after a prompt change, improving from 14/21 to 21/21 correct answers.
- **Policy retrieval: 58% → 92%.** A relevance threshold improved handling of off-topic questions. These results use the local embedding model; I still need to repeat the evaluation with the production provider.

[Full report](evals/primary_results.md) · [Methodology](evals/methodology.md)

## See it in action

![An ambiguous refund request is refused, with its execution trace and evaluation results available for inspection.](docs/img/ambiguous-refusal-demo.gif)

The demo uses seeded data that resets daily. Try the ambiguous refund scenario to see how the system handles a request without enough information to identify the customer.

## What the evals found

My original SQL checks verified that a query was safe to run. They missed two calculation errors, including a refund rate that counted order lines where it needed units sold.

I added assertions against answers calculated directly in the database. Those checks exposed the errors and guided a SQL prompt change. The seven cases then passed across three runs.

The [case study](CASE_STUDY.md) follows the investigation, including the retrieval and extraction failures that surfaced later.

## How it works

![Architecture diagram showing the agent loop, SQL and policy tools, execution controls, and request logging.](docs/img/architecture-diagram.svg)

For data and policy questions, Claude chooses between SQL and policy retrieval inside a capped loop. Generated queries pass validation and run through a restricted database role. After generation, the grounding check compares cited policy names and numbers with the retrieved passages.

Refund requests follow a separate path. Claude extracts the requester, product, and reason. Application code resolves the order and applies the refund rules to return a decision.

Request logs record outcomes and timing. The combined workflow also records tool calls for inspection.

**Built with:** Python, FastAPI, Claude, PostgreSQL/pgvector, SQLAlchemy, Next.js, and Docker.

[Architecture](ARCHITECTURE.md) covers each component and its execution controls.

## Known limitations

- **Retrieval:** One known phrasing ranks the wrong policy passage first under the production embedding model. I calibrated the thresholds on a small, hand-labeled sample.
- **Evaluation coverage:** Categories contain 2–12 cases each. They help catch regressions in the tested scenarios; broader accuracy needs a larger dataset.
- **Judge validation:** I checked the judge against 33 human-labeled verdicts, all from passing outcomes. Its ability to recognize failures remains unmeasured.
- **Authentication:** Demo roles come from a caller-set header. Real customer use would require verified identity and access controls.

## Run locally

Requires Python 3.14, Poetry, Node/pnpm, and Docker. Follow [Setup and deployment](docs/DEPLOY.md) for environment configuration and startup commands.

## More detail

- **[Case study](CASE_STUDY.md)** — what the evaluations uncovered and how the findings changed the work.
- **[Architecture](ARCHITECTURE.md)** — request flow, execution controls, and implementation details.
- **[Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab)** — evaluation results and methodology.
- **[Deployment](docs/DEPLOY.md)** — local setup and deployment instructions.
