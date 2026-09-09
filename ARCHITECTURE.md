# Architecture

I designed the system to let Claude interpret requests and choose tools while application code controls execution. Data questions can use SQL and policy retrieval together. Refund requests follow a separate path, where code applies the policy rules.

A useful answer needs the right evidence and permission to use it. This document follows a request through the system, including what happens when either is missing. The [decision log](DECISIONS.md) records the reasoning behind individual changes.

## What happens when someone asks a question?

![Architecture diagram showing the agent loop, SQL and policy tools, execution controls, and request logging.](docs/img/architecture-diagram.svg)

Consider a request asking about refund rates and the relevant refund policy.

1. The orchestrator gives Claude access to SQL and policy retrieval tools.
2. Claude proposes a tool call. A generated SQL query passes validation before running through a restricted database role.
3. The tool returns its results. Claude can request more evidence within a loop capped at four rounds.
4. Claude generates an answer. The grounding check compares cited policy names and numbers with the passages retrieved during that request.
5. The request log records the outcome and execution details.

The orchestrator calls the same query and retrieval services used by the direct endpoints. Their controls apply wherever those services are called.

If Claude keeps requesting tools after the loop limit, the API returns an explicit incomplete response.

### Who decides whether a refund qualifies?

A refund decision depends on policy rules and the order itself. I kept that decision in application code so I could trace each outcome to a specific rule and test it against known orders.

Claude extracts fields from the request, including the requester, product, and reason. The application resolves the order, then applies the refund rules in order. The first matching rule determines the outcome.

Depending on the policy, the result can approve or deny the request, require manager approval, or flag it for review. The response identifies the applicable rule. If the application cannot resolve the customer or product, it returns `could_not_process`.

The evaluator reads order data and returns a decision. It does not update the refund record.

## What can the model execute?

### Which tools can the caller use?

A shared tool registry defines the permission each tool requires. The permission dependency looks up that requirement by tool name and checks it against the caller’s role.

This check covers the SQL, policy retrieval, ticket, and invoice endpoints. Drafting and confirming a ticket or invoice use separate tool entries, allowing them to require different permissions.

The analyze and refund endpoints currently use read-only operations and are available to every demo role. Roles come from a caller-set header, so this setup demonstrates permission behavior without establishing the caller’s identity.

### What keeps a query within its allowed access?

Generated SQL passes through validation that restricts statements and database access. The checks reject prohibited queries, including attempts to select `customers.email`.

A cost check uses Postgres’s `EXPLAIN` estimate to reject expensive queries. Execution then uses the restricted `ops_agent_readonly` role.

I added database permissions as an independent control. If application validation misses a prohibited operation, Postgres still enforces the role’s grants.

Those grants need verification too. My first attempt granted access to the customers table, then revoked access to email. A direct query under the restricted role still returned email because the table-wide grant remained in effect. I switched to explicit allowed-column grants and checked the read again. [Decision 6](DECISIONS.md#6-layer-3-column-restriction-allowlist-grant-not-table-grant-then-revoke) records the investigation.

The refund evaluator uses its own role, `refund_evaluator_readonly`, limited to the tables it needs. It can read customer email to resolve a request. That field is excluded from the evaluator’s response.

### What if the documents cannot answer the question?

Retrieval needs a way to return no evidence when a question falls outside the corpus. Policy documents are split into passages with source metadata. Retrieval compares their embeddings with the question and filters candidates using a calibrated distance threshold.

When no passage qualifies, retrieval returns no supporting evidence. The answer path can then report that the available documents do not support an answer.

The threshold depends on the embedding provider. Local development and production use different models, each with its own calibration.

### How do we check a policy answer?

A policy citation gives the reader something to inspect. I added a grounding check that compares cited rule names and numbers with the passages retrieved for that request.

A matching citation still leaves a question open: did the answer apply the rule correctly? In calibration, an answer claimed a retrieved rule had been “waived.” The citation matched, so the check passed it. The [case study](CASE_STUDY.md#6-checking-the-measurement-tools) explains what that test revealed.

Topic coverage checks for claims about subjects the available tools cannot support. Both checks can produce warnings for the user. The generated answer remains visible.

These checks have false positives. For example, mentioning a rule while explaining that it does not apply can still trigger a warning. Calibration findings and coverage gaps are documented in [EVALS.md](EVALS.md).

## What happens when a request fails?

Someone using the assistant needs to know whether a request completed. I made failures visible in the API response and request logs so a rejected query or exhausted tool loop has an explicit outcome.

| Condition | System behavior |
|---|---|
| SQL fails validation or exceeds the cost limit | The query is rejected before execution. |
| A covered model call encounters a transient failure | The SQL and analyze paths allow one retry, with a timeout and fixed delay. |
| Both attempts fail | The path returns its structured error or incomplete response. |
| The tool loop reaches its limit | Analyze returns an explicit incomplete response. |
| A refund request cannot be matched to a customer or product | The evaluator returns `could_not_process`. |
| Retrieval finds no qualifying passages | The tool returns no supporting policy evidence. |
| An answer cites a policy rule that was not retrieved | The grounding check flags the answer. |

Retry handling currently covers the SQL proposal and analyze calls. Other model-call sites remain outside that wrapper.

Request logs capture outcomes and latency. Token usage and estimated cost are populated where model calls occur. Analyze requests also carry an ordered tool-call trace.

[Inspect a request in System Traces](https://ecom-workflow-agent-web.vercel.app/activity) to see the recorded outcome and available execution details. Failure tests exercise the retry behavior and incomplete responses; [EVALS.md](EVALS.md) explains how those checks fit into the suite.

## Data and deployment

### Business data

The demo uses seeded e-commerce records, including customers, orders, refunds, and support activity. Additional fixtures support shipment questions and campaign analysis.

The seed script recreates known scenarios for testing. Production reseeds daily, independently of application deployments.

Vendor invoices and operational records, such as request logs, have their own storage. The seeded business tables represent only part of the schema.

### Policy documents

Local development uses `BAAI/bge-m3` to embed policy passages. Production uses Voyage AI because the local model’s memory requirements exceeded the deployment environment.

Changing providers changes retrieval behavior. I calibrated relevance thresholds separately, and one known production ranking failure remains open.

### Hosting

Vercel hosts the frontend. Render hosts the API and database, along with the scheduled reseed job.

The frontend proxy adds a shared secret to API requests. Backend middleware checks that secret. CORS separately restricts browser access by origin.

Environment configuration and startup commands are in [Setup and deployment](docs/DEPLOY.md).

## Scope and open gaps

The SQL and policy paths, refund evaluation, request tracing, and ticket and invoice draft/confirm flows are implemented.

An investigation pipeline also has a Planner and Data Analyst that gather evidence for questions such as “Why did revenue drop last week?” It is tested directly but has no endpoint or final stage for writing an answer. [Decision 45](DECISIONS.md) records the deferral.

Real customer use would require verified identity and tenant isolation. Sensitive-column handling currently centers on the explicit `customers.email` restriction; a broader classification policy is still needed.

Model routing and further retrieval work remain in [LATER.md](LATER.md).

## Implementation references

| Component | Source |
|---|---|
| Analyze loop | [analyze_service.py](apps/api/app/orchestrator/analyze_service.py) |
| SQL generation | [claude_client.py](apps/api/app/query/claude_client.py) |
| SQL validation | [validation.py](apps/api/app/query/validation.py) |
| Policy retrieval | [service.py](apps/api/app/rag/service.py) |
| Policy ingestion | [ingest.py](apps/api/app/rag/ingest.py) |
| Refund extraction | [refund_extraction.py](apps/api/app/orchestrator/refund_extraction.py) |
| Refund rules | [refund_evaluator.py](apps/api/app/orchestrator/refund_evaluator.py) |
| Answer checks | [groundedness.py](apps/api/app/orchestrator/groundedness.py), [topic_coverage.py](apps/api/app/orchestrator/topic_coverage.py) |
| Permissions | [permissions.py](apps/api/app/permissions.py) |
| Request logging | [observability](apps/api/app/observability/) |

### Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | Python 3.14, FastAPI, SQLAlchemy |
| Model | Claude through the Anthropic Python SDK |
| Storage | PostgreSQL with pgvector |
| Embeddings | Local BAAI/bge-m3; hosted Voyage AI in production |
| Testing | pytest and a separate evaluation runner |
