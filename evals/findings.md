# Findings

I investigated failures in the agent and in the checks used to evaluate it. Each finding below explains what I observed, how I checked it, and what changed.

## Finding 1: The sql-05 evaluation bug

### What happened

`sql-05-write-attempt-rejected` asked the agent to approve every pending refund. Claude generated an unrelated read-only query. Checking only for a `rejected` response could not establish whether the validator had blocked an attempted write.

### What I checked

I inspected the generated query and the expected response. The case combined model behavior with a test of deterministic enforcement, while depending on the model to propose the prohibited operation.

### What changed

I removed the flawed case and moved write-blocking checks to direct validator tests. Unsupported-action responses needed their own expectations. The case study records how that led to further investigation of `mixed-08`.

## Finding 2: SQL calculation errors

### What happened

The generated refund-rate query passed structural checks but returned 50.00%. The independently calculated answer was 43.48%.

### What I checked

I compared returned values with calculations made directly in Postgres. The query counted order-item rows and lost the quantities within those rows. A second case also included a denied refund.

Across seven cases run three times, structural safety held on all 21 attempts. Only 14 returned the correct answer.

### What changed

I added result assertions and clarified the SQL prompt. The seven cases then passed across three runs. `primary_results.md` identifies the source experiments.

## Finding 3: Citation-check calibration

### What happened

The grounding heuristic flags policy citations absent from retrieved evidence. I tested whether those flags agreed with human labels.

### What I checked

The sample contained 20 examples: 12 from request traffic and eight constructed edge cases. A positive means the checker flagged the answer as ungrounded.

| Outcome | Count |
|---|---:|
| Correctly flagged | 2 |
| Incorrectly flagged | 5 |
| Missed a problem | 2 |
| Correctly left unflagged | 11 |

Precision was 28.6%, recall was 50%, and the false-positive rate was 31.2%. These figures describe this small sample.

One missed example claimed that a retrieved rule had been waived. The citation matched, but the passage did not support that claim.

### What changed

I documented the limitation: citation matching establishes that a source was retrieved, not that the answer applied it correctly. `groundedness_calibration_raw.json` preserves the examples. The results do not establish the detector's error rate on broader traffic.

## Finding 4: Cache contamination

### What happened

Cached responses could hide the effects of changing a model or retrieval configuration.

### What I checked

I inspected 2,235 request-log rows and found no marked cache reuse in the audited runs. A separate retrieval experiment did reuse a baseline response across later configurations. All variants showed zero successful off-topic refusals, including the configuration with a threshold.

### What changed

I added an explicit cache bypass and reran the affected retrieval cases. `experiment_history.md` records the correction. Each experiment's cache setting belongs alongside its results.

## Finding 5: Differences in the deployed environment

### What happened

A policy question answered locally returned a false “I don't know” in the deployed app. Local evaluation used BAAI/bge-m3; production used Voyage because the local model exceeded the deployment memory budget.

### What I checked

I ran the exact generated search query, “damaged shipments policy,” against both providers with the same corpus.

| Environment | Relevant passage rank | Distance |
|---|---:|---:|
| Local | 2nd | 0.4191 |
| Voyage | 4th | 0.6101 |

### What changed

I calibrated separate thresholds: 0.46 locally and 0.48 for Voyage. This addressed other retrieval failures. The specific damaged-shipments phrasing remained unresolved. `measurement_context.md` records the configurations.

Testing the deployed refund endpoint also exposed an extraction failure. Claude treated “2 Ergonomic Desk Chairs” as a product name, which failed to match “Ergonomic Desk Chair” in the database.

The refund-rule cases supplied pre-extracted fields and bypassed that step. I corrected the extraction behavior and verified the expected `requires_manager_approval` response through the live endpoint. Coverage of the extraction path needs to accompany tests of the refund rules.
