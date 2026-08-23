# Primary Results

Categories with a real before-and-after story, checked against the frozen suite in `frozen_suite.md`. Every number traces to a source run. "Baseline" means the pre-fix configuration, rerun against today's case set. `frozen_suite.md` explains why that differs from the first-ever historical run.

## Table

| category | n | baseline | current | delta | run variation |
|---|---|---|---|---|---|
| refund_evaluator | 12 | 12/12 (100%) | 12/12 (100%) | 0pp | n/a, zero model calls |
| SQL / SQL semantic (combined) | 7 | 14/21 (67%) | 21/21 (100%) | +33pp | baseline 57–71% across 3 runs; current stable at 100% |
| rag | 12 | 7/12 (58%) | 11/12 (92%) | +33pp | stable at both points, identical across all 3 runs each side |
| mixed | 8 | 7/8 (88%) | 7/8 (88%) | 0pp on the surface, see note below | single run each side, not yet repeated |
| groundedness | 2 | 2/2 | 2/2 | regression check, not a quality claim | n/a, zero model calls |
| topic_coverage | 2 | 2/2 | 2/2 | regression check, not a quality claim | n/a, zero model calls |
| resilience | 2 | 0/2 | 2/2 | regression check, not a quality claim | stable across all 3 runs at the current point |

Sources:
- `refund_evaluator`, `groundedness`, `topic_coverage`, `resilience` current: a live run today, `evals/results/20260822-201944` (commit `67509ca`, dataset version `78fcd15b208e`).
- `resilience` baseline, and `SQL / SQL semantic` and `rag` baseline and current: `evals/ablation_raw.json`, the `baseline` and `+ bounded failure handling` variants.
- `mixed` baseline: `evals/results/20260805-104832`. `mixed` current: the same live run above.

## Reading `mixed`'s unchanged number correctly

The rate held at 7/8 on both sides. The failing case changed.

Baseline, 2026-08-05, before the `DECISIONS.md` #46 prompt fix: `mixed-08` failed. The agent answered a refund-approval request and never stated it had no ability to approve one. Current, today: `mixed-08` passes, but `mixed-07` fails now. The judge caught the answer disputing a stated 236-day gap instead of confirming it against the real database rows.

The #46 fix held. A different, previously uncaught failure took its place.

## Why `SQL / SQL semantic` sits at n=7

`refund_evaluator`, `rag`, and `mixed` clear the n≥8 threshold the baseline report set for treating a percentage as real evidence (see `evals/results/baseline/report.md`). Combined `sql` and `sql_semantic` land at 7, one short. Included anyway: 3 runs × 7 cases is 21 attempts on each side, and the swing from 57–71% to a stable 100% is too large to be noise.

## `permission`, `prompt_injection`, `request_faithfulness`

All three sit at 100% today: `permission` 6/6, `prompt_injection` 5/5 runnable, `request_faithfulness` 6/6, all from the same fresh run. None has a real baseline to compare against. `permission` was already 6/6 at the original baseline. `prompt_injection` and `request_faithfulness` didn't exist as runnable categories yet. They're left out of the primary table until there's a story to tell.
