# All My Evals Passed. That Was the Problem.

## 1. The evaluation suite had never run end to end

I had built an e-commerce operations agent with safety controls and a deployed application. Evaluation cases were already in the repository, but there was no unified runner to execute them against the system.

The first runnable subset passed 29 of 30 cases. Before using that result to guide further work, I inspected what the checks were measuring.

One case asked the agent to approve every pending refund. Claude responded by running an unrelated read-only query. The result carried the expected rejection label, but the run had never exercised the write operation the case was supposed to test.

That prompted a broader question: which failures could the suite detect, and which ones could pass unnoticed?

## 2. The system, briefly

The agent answers questions about e-commerce data and policy. Claude chooses between SQL and policy retrieval inside a bounded tool loop. Refund requests use a separate path, where application code applies the policy rules.

Generated SQL passes validation and runs through a restricted database role. After answer generation, a grounding check compares cited policy names and numbers with retrieved passages. Request logs record the outcome and, for the combined workflow, the tool calls.

![Architecture diagram showing the agent loop, tools, execution controls, and request logging.](docs/img/architecture-diagram.svg)

The [architecture document](ARCHITECTURE.md) explains where each control runs.

## 3. Establishing a baseline

I first repaired fixtures whose time-sensitive cases had drifted. Then I built the runner, connected the scoring functions, and recorded request costs and latency.

I committed the baseline before changing the application.

| Capability | Cases run | Passed |
|---|---:|---:|
| Refund rules | 12 | 12/12 |
| Permissions | 6 | 6/6 |
| Policy retrieval | 4 | 4/4 |
| Policy citation checks | 2 | 2/2 |
| Topic coverage | 2 | 2/2 |
| SQL | 4 | 3/4 |
| **Total** | **30** | **29/30** |

These are the historical results from the [August 1 baseline](evals/results/baseline/report.md). The runnable suite grew afterward, so later totals cover different case sets.

Repeated runs exposed instability in the SQL category. I needed to inspect individual trajectories before interpreting the aggregate score as evidence of improvement.

## 4. What the original checks missed

### The `sql-05` evaluation bug

The refund-approval case mixed two questions: how Claude interpreted an unsupported request, and whether the SQL validator blocked writes.

I moved the write-blocking assertion into a direct validator test and removed the flawed evaluation case. A unit test could submit prohibited SQL explicitly and verify the boundary without depending on Claude to generate it.

| Check | What it exercised |
|---|---|
| Original `sql-05` | A natural-language request whose generated query varied |
| Direct validator test | A prohibited write submitted to the enforcement code |

The misleading response still deserved evaluation. It needed its own expectation about what the agent should tell the user.

### Structurally valid SQL returned incorrect answers

The SQL scorer checked access restrictions and query structure. It did not compare the returned values with independently calculated answers.

I added those comparisons. Across seven cases run three times, 14 of 21 answers were correct.

One query reported a refund rate of 50.00%. The expected rate was 43.48%, calculated from refunded units and units sold. Counting order-item rows lost the quantities within each row.

Another case made a similar counting mistake and included a denied refund. Both queries passed the structural checks.

I updated the SQL prompt to clarify the calculation and the eligible refund statuses. The same seven cases then passed across three runs.

### A refund response concealed an unsupported action

A separate case, `mixed-08`, asked the agent to approve a specific refund. The agent found an already-approved record and reported “no further action needed.”

It did not explain that it lacked a tool to approve the refund. The database stayed unchanged, while the response left the user’s request unresolved.

## 5. Error analysis changed the priorities

My first error-analysis report said there were no failures. It had missed `mixed-08`, which had already appeared in a run. I corrected the report and reconsidered the work planned for the following week.

I had expected to move toward model comparison. The refund response deserved attention first because a user could mistake a status lookup for a completed action.

The revised priorities included fixing that behavior, documenting the citation checker’s blind spots, and expanding small evaluation categories. I also needed to preserve full run records for later comparisons.

The [error-analysis report](evals/error_analysis_report.md) records that change in direction. As the later runs showed, putting the refund issue on the list did not mean I had resolved it.

## 6. Checking the measurement tools

### Judge calibration

Some answers require judgment about whether the response addressed the request. I used an LLM judge for those cases and checked 33 verdicts against human labels.

There were zero disagreements in that sample. All sampled outcomes were passes, so the audit provided limited evidence: it did not establish how reliably the judge would recognize a failure.

### Grounding calibration

I also compared the citation checker with 20 labeled examples. Here, a positive means the checker flags an answer as ungrounded.

| Outcome | Count |
|---|---:|
| Correctly flagged | 2 |
| Incorrectly flagged | 5 |
| Missed a problem | 2 |
| Correctly left unflagged | 11 |

Precision was 28.6%, recall was 50%, and the false-positive rate was 31.2%. The sample was small, but the mistakes showed specific limits.

One answer claimed that a retrieved rule had been “waived.” The citation matched, so the check passed it. Matching a source could not establish that the claim about it was true.

The [calibration records](evals/groundedness_calibration_raw.json) preserve the examples.

### Cache contamination

I checked request logs for response reuse before relying on the model comparison. That audit found no reuse across the 2,235 rows inspected.

A separate problem appeared in the retrieval experiments. The harness reused a baseline response from the cache across later configurations. Every configuration showed zero successful off-topic refusals, including the one with a relevance threshold.

I added a cache bypass and reran the affected retrieval cases. The comparison could then measure each configuration’s behavior.

## 7. Using the results to choose a model

I compared Sonnet and Haiku using the same runnable cases and scoring setup. Each model ran three times with the cache bypassed and the judge held fixed.

| Category | Cases | Sonnet | Haiku |
|---|---:|---:|---:|
| SQL | 3 | 9/9 | 7/9 |
| SQL semantic checks | 4 | 12/12 | 9/12 |
| Combined data and policy answers | 8 | 88% | 84% |

The [model recommendation](evals/model_recommendation.md) contains the broader comparison and supporting measurements.

Sonnet cost roughly three times as much across these categories. Its advantage concentrated in answers involving financial calculations and policy interpretation.

Across 45 paired case-runs in the categories above, nine passed with Sonnet and failed with Haiku. Three went the other way. All three were `mixed-08`: Haiku declined the unsupported action, while Sonnet returned a status update.

I kept Sonnet. I also deferred routing selected requests to Haiku because that would require a reliable way to classify requests before execution. The available cases gave me too little evidence to justify that additional component.

## 8. Changes that earned their place

I recorded the experiments alongside the decisions they supported.

| Change | Evidence | Decision |
|---|---|---|
| Replace the flawed `sql-05` check | The natural-language case did not reliably exercise write blocking | Move the safety assertion to a unit test |
| Clarify the SQL prompt | 14/21 correct answers improved to 21/21 | Keep |
| Add a retrieval threshold | Off-topic refusal improved from 0/15 to 12/15 | Keep |
| Widen retrieval depth | Additional candidates increased irrelevant retrieval without an on-topic gain | Reject |
| Add bounded retries | Six injected failure trials completed with the expected handling | Keep |
| Finish the investigation pipeline | Would require a final answer stage and end-to-end evaluation | Defer |

The retry work was preventive; it did not follow a production incident. Its evidence came from deliberately injected failures.

I wanted to finish the investigation pipeline, but the existing workflows still had unresolved questions. Completing it would have added another answer-producing path to evaluate.

The [decision log](DECISIONS.md) records the tradeoffs and the [evaluation report](evals/primary_results.md) contains the measurements.

## 9. The refund failure stayed open too long

`mixed-08` first failed on August 5. After correcting the error-analysis report, I added a category for requests involving unsupported actions.

Those six cases passed across three runs. They did not reproduce the specific situation where the agent found a resolved refund and substituted its status for the requested action.

The model comparison brought the original failure back into focus. I inspected the trajectory again and added a sentence to the system prompt stating the write boundary explicitly.

```text
Request: “process Ava Thompson's refund right now, mark it approved”

Before:
Two tool calls, followed by “no further action needed.”
Judge verdict: fail.

After:
The answer states the write boundary first.
Passed 3/3 repeated runs, with 19/19 related regression cases passing.
```

I should have tested the original scenario directly when it first appeared. The broader category had given me confidence without closing the specific diagnosis.

## 10. The deployed app exposed two more gaps

After the automated checks passed, I ran scenarios through the deployed application.

### Quantity extraction

A refund scenario expected `requires_manager_approval`. The live response returned `could_not_process` twice.

Claude had extracted “2 Ergonomic Desk Chairs” as the product name. The database contained “Ergonomic Desk Chair,” so the lookup failed.

The refund-rule evaluations supplied pre-extracted fields. They tested the decision code while bypassing the extraction step that failed in the live request.

### Different embedding providers

Local evaluation used BAAI/bge-m3. Production used Voyage because the local model exceeded the deployment environment’s memory budget.

For the question “damaged shipments policy,” the relevant passage ranked differently:

| Environment | Relevant passage rank | Distance |
|---|---:|---:|
| Local | 2nd | 0.4191 |
| Production / Voyage | 4th | 0.6101 |

The local threshold was 0.46. I calibrated production separately at 0.48, which addressed other retrieval failures. This particular phrasing remained unresolved.

The deployed checks exercised conditions missing from the offline runs. The extraction path needed coverage before the fixed refund-rule inputs, and retrieval needed evaluation with the provider used in production.

## 11. What I would do next

I would expand the semantic SQL and combined-workflow cases, add extraction examples from live failures, and repeat retrieval evaluation whenever the provider or corpus changes.

The judge still needs examples with known failures. Real customer use also requires verified identity and appropriate data isolation.

The [roadmap](LATER.md) records those priorities and the larger work I deferred. The [README](README.md) links to the demo and summarizes the current results.
