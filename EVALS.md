# Evaluation suite

I use evaluations to check whether changes improve the assistant's behavior on known cases. The dataset contains 79 cases across 13 categories. The runner supports 11 categories, with three additional cases skipped within prompt injection. A full run currently scores 62 cases.

This document describes the cases and their coverage. See [Running evaluations](evals/README.md) for commands, or the [Evaluation Lab](https://ecom-workflow-agent-web.vercel.app/evaluation-lab) for saved results. The [case study](CASE_STUDY.md) explains how failures changed the work.

## What the cases measure

| Category | Cases | What it checks | In deterministic CI subset |
|---|---:|---|---|
| `refund_evaluator` | 12 | Refund outcome and applicable rule over seeded orders | Yes |
| `rag` | 12 | Retrieval of expected policy passages and off-topic handling | No |
| `mixed` | 8 | Tool use, completion, and answer quality in the analyze workflow | No |
| `invoice_evaluator` | 8 | Invoice workflow expectations; runner not implemented | No |
| `prompt_injection` | 8 | Resistance to embedded instructions; five cases runnable | No |
| `ticket_evaluator` | 6 | Ticket workflow expectations; runner not implemented | No |
| `permission` | 6 | Whether a demo role can use an endpoint | No |
| `request_faithfulness` | 6 | Whether the answer acknowledges unsupported actions | No |
| `sql_semantic` | 4 | Calculations where valid SQL can return a plausible wrong value | No |
| `sql` | 3 | Query structure and expected results | No |
| `groundedness` | 2 | Citation checks on fixed answers and retrieved passages | Yes |
| `topic_coverage` | 2 | Unsupported-topic checks on fixed answers and tool evidence | Yes |
| `resilience` | 2 | Retry and failure behavior with mocked model errors | Yes |

The 18-case CI subset makes no live model calls. Permission scoring checks status codes, but allowed requests can call Claude, so that category stays outside the subset.

## How scoring works

### Fixed outcomes

Refund cases call the evaluator with known inputs and compare its decision with the expected policy rule. They bypass natural-language extraction, so they cannot establish that Claude extracts a customer's request correctly.

Groundedness and topic coverage cases feed fixed inputs into the answer checks. Resilience cases mock model failures and inspect the response and request log. These tests cover the checks themselves, with limited examples of each behavior.

### SQL and retrieval

SQL cases check structural properties and compare returned rows with independently calculated answers where `expected_result` is defined. Some structural assertions use text matching, which can misread aliases or names inside comments. The application has its own SQL parser for execution validation.

Retrieval cases check expected rules and rejection of off-topic questions. They do not establish that a generated answer applies the retrieved policy correctly. Results depend on the embedding provider and its configured threshold.

### Judged answers

The mixed, prompt-injection, and request-faithfulness categories use an LLM judge to assess prose against written criteria. The application model and judge are configured separately. Using similar models can still introduce shared blind spots.

Only `resisted` passes the injection rubric. Request faithfulness accepts `honest_refusal` or `transparent_redirection`. Other verdicts, including insufficient evidence, fail those checks.

The dataset also records review status through its `scoring` field. A `manual_review` label does not necessarily mean the runner makes no judge call. Human verdicts live in [labels.json](evals/labels.json); the [methodology](evals/methodology.md) explains the review process.

## How a case is defined

Cases live in [cases.json](evals/cases.json). Each has six fields:

| Field | Purpose |
|---|---|
| `id` | Stable case identifier |
| `category` | Workflow or behavior under test |
| `input` | Request text or serialized input for a direct function check |
| `expected` | Required outcomes, properties, or calculated values |
| `scoring` | `exact_match`, `rule_based`, `manual_review`, or `ai_judge` |
| `failure_trap` | The mistake the case is intended to expose |

Expected SQL values include their derivation where recorded. Refund expectations were traced against policy text and seeded orders. For example, `refund-04` and `refund-05` exercise the defective-item and changed-mind windows, so a single default window cannot satisfy both cases.

Groundedness cases serialize an answer and retrieved chunks together inside `input`. Read the category's runner when interpreting that field.

## Coverage limits

- **Customer data:** Cases use seeded records and small categories of 2–12 examples. Passing results apply to those cases and configurations.
- **Judge validation:** The calibration covered 33 human-labeled verdicts, all passing outcomes. Detection of failing answers remains unmeasured.
- **Deployment coverage:** Refund cases bypass extraction. Local retrieval runs also miss differences introduced by the production embedding provider. Both gaps have concealed real failures.
- **Request faithfulness:** All six dedicated cases are bulk requests. The single-order failure discussed in the case study lives in `mixed-08`.
- **Cost and efficiency:** Judged-category cost excludes the judge call. Tool-call counts are recorded but do not carry an efficiency pass/fail threshold.
- **Failure display:** A scalar result shown in a failure record can select an unrelated numeric value. Inspect the saved rows and generated SQL when diagnosing a calculation.

The [grounding calibration](evals/groundedness_calibration.md) and [request-faithfulness review](evals/request_faithfulness_calibration.md) document narrower checks and their blind spots.

## Out of scope

Ticket and invoice draft/confirm flows exist in the API, but their evaluation categories lack runners. Two injection cases also need the ticket harness; another requires an image input. These are skipped, not counted as passing.

Historical fixes and before/after measurements live in [Primary results](evals/primary_results.md) and [Experiment history](evals/experiment_history.md). Keeping those reports separate makes it easier to distinguish suite coverage from a particular run's outcome.
