# Public evaluation report — first pass

Route: `/evaluation-report`. Linked from Evaluation Lab and the repository README.

## Scope

Explain the agent, reconcile coverage, show saved category results, judge agreement, category median/p95 harness latency and recorded model cost, and one SQL before/after comparison. No new suite run, charts, filters, or redesign.

## Verified provenance

| Measurement | Source | Sample and interpretation |
| --- | --- | --- |
| Defined cases/categories | `cases.json` | 79 cases, 13 categories; byte hash `78fcd15b208e` matches saved run metadata |
| Scored outcomes | `results/20260822-201944/results.json` | 62 scored, 60 passed, 2 failed; 14 unsupported ticket/invoice cases plus 3 injection cases skipped |
| Category latency | Same saved run, per-case `latency_ms` | One observation per scored case, grouped by category, including failures; median and nearest-rank p95; harness wall time includes judge work where used |
| Category cost | Same saved run, per-case `cost_usd` | Mean of non-null application-model estimates, with observed n shown; judge, hosting, and unrecorded embedding costs excluded; null is not zero |
| Human/judge agreement | `labels.json` | 15/15 agreements across 15 case IDs, all pass outcomes |
| Additional agreement audit | `request_faithfulness_labels.json` | 18/18 agreements across 6 case IDs × 3 runs; accepted refusal/redirection outcomes; not evidence of failure detection |
| SQL before/after | `ablation_raw.json` | Baseline 14/21 versus bounded-failure-handling variant 21/21; 7 SQL questions × 3 runs per configuration; bundled changes, not isolated attribution |
| Environment | Saved `experiment.json` and `measurement_context.md` | Historical local run, commit `67509ca`, SQL v2 / analyze v2, local embeddings; not the current deployed analyze-v3 configuration |

The public page links every source. The label files lack full run/model metadata; the ablation artifact lacks a recorded commit. Those gaps are stated rather than filled in by inference. Historical results and case expectations were not rewritten.

## Next missing measurement — stop here

Repeat SQL metric checks through the current `/query/analyze` path with cache bypass and independent expected results. Record deployed configuration, prompt and dataset versions, repeated outcomes, app-only latency, and model cost. The two manual deployment checks are examples, not a replacement for this measurement.
