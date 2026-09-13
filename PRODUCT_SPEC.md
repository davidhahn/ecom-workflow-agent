# Product scope

I built an e-commerce operations assistant to explore how natural-language requests can work with business data and policy rules. This document describes the intended users, the workflows available today, and the limits of the demo.

The project began with SQL analysis and policy retrieval. Refund evaluation and other workflows followed. The [decision log](DECISIONS.md) preserves those earlier scope choices; [Architecture](ARCHITECTURE.md) describes the current implementation.

## Who is it for?

The intended users are support staff and operations analysts. A refund question can require an order lookup, a policy check, and a decision about whether a manager needs to review it. Reporting questions require agreement on what a metric means before calculating it.

The assistant provides a plain-language interface to that work. The intended benefit is less manual lookup and more consistent handling of routine questions. This is a portfolio project using seeded records; customer adoption and time savings have not been measured.

Engineers and reviewers can also inspect requests through System Traces and examine saved evaluation results. Those interfaces help explain what the system did and where its behavior needs further work.

## What can someone do?

| Workflow | Example | Current behavior |
|---|---|---|
| Ask about business data | “Which product category has the highest refund rate?” | Queries seeded records and returns an answer based on the results |
| Look up policy | “What does our policy require before a damaged-shipping refund can be processed?” | Retrieves policy passages and uses them to answer |
| Combine data and policy | Ask for a refund-rate calculation and the relevant policy | Can use both tools within the same bounded workflow |
| Evaluate a refund | Paste a customer's refund request | Extracts details, resolves an order, and applies fixed refund rules |
| Inspect a request | Open a result's execution trace | Shows the recorded outcome and available execution details |

Refund evaluation can approve or deny a request, require manager approval, or flag it for review. An unresolved request returns `could_not_process`. The evaluator returns a decision without issuing the refund or updating its record.

The API also supports ticket and invoice draft/confirm flows. Drafts require a separate confirmation request with write permission before a business record is inserted. These flows have no dedicated frontend screens. See the [API guide](apps/api/README.md) for endpoint details.

## What should the experience make clear?

**What the system used.** Answers should give users evidence they can inspect. Combined requests record tool calls, and policy answers expose citations that can be compared with retrieved passages.

**What completed.** Rejected queries and exhausted tool loops need explicit outcomes. A response should acknowledge an unsupported action rather than leave the user thinking it was performed.

**What needs review.** Citation warnings remain visible alongside the answer. Matching a cited rule to a retrieved passage does not establish that the answer applied it correctly.

**What the user can change.** Missing customer details stop refund evaluation. The current interface does not conduct a follow-up conversation to resolve that ambiguity.

These are product expectations. The evaluations test selected examples of them; they do not guarantee every generated response meets them.

## Where are the boundaries?

Generated SQL runs through validation, cost checks, and a restricted database role. The model cannot use that path to write business records. Refund decisions follow a separate rules engine, with extracted fields checked against database records.

The application still has limits that matter to users:

- **Identity and access:** Demo roles come from a caller-set header. The backend proxy secret does not verify the end user. Verified identity and tenant isolation are required before connecting customer data.
- **Refund coverage:** The evaluator uses the full order-line quantity. It does not support partial-quantity refunds or a persisted process for collecting missing evidence.
- **Answer accuracy:** Allowed SQL can calculate the wrong value. Retrieval has a known production ranking failure, and citation checks can miss misinterpretations.
- **Customer resolution:** Requiring a customer identifier prevents the missing-customer fallback. It does not authenticate that person or resolve every possible order match.

An investigation pipeline has a tested Planner and Data Analyst, but no endpoint or final report-writing stage. Open-ended investigation is not a completed product workflow. [Decision 45](DECISIONS.md#decision-45) records the deferral.

## How do I judge whether it works?

For the demo, I check calculations against independently derived answers, retrieval against expected passages, and refund outcomes against policy rules and seeded orders. Fixed-input tests exercise execution restrictions and failure handling.

The refund-rule evaluations bypass natural-language extraction, so passing those cases does not validate the full request path. Deployment checks exposed that gap. [EVALS.md](EVALS.md) describes coverage, while the [case study](CASE_STUDY.md) follows the resulting fixes.

A customer pilot would need its own success criteria. I would start with one workflow, measure its current handling time and correction rate, and agree on which errors require human review or stopping the pilot. Those business outcomes remain unmeasured here.

## Try it or explore further

[Run a scenario](https://ecom-workflow-agent-web.vercel.app/scenarios) to inspect an example request and its outcome. The [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab) provides saved measurements and their scope.

The [roadmap](LATER.md) tracks proposed work. Implementation details and setup belong in [Architecture](ARCHITECTURE.md) and [Setup and deployment](docs/DEPLOY.md).
