# Primary Results

This table covers every category with a real before-and-after story: a measured change tied to a specific fix. Every number in it traces back to a specific source run, listed below the table. "Baseline" means the configuration before a fix landed, rerun against today's fixed case set. That's different from the very first run this project ever recorded, and `frozen_suite.md` explains why that distinction matters.

## Table

| category | n | baseline | current | delta | run variation |
|---|---|---|---|---|---|
| refund_evaluator | 12 | 12/12 (100%) | 12/12 (100%) | 0pp | n/a, zero model calls |
| SQL / SQL semantic (combined) | 7 | 14/21 (67%) | 21/21 (100%) | +33pp | baseline 57–71% across 3 runs; current stable at 100% |
| rag | 12 | 7/12 (58%) | 11/12 (92%) | +33pp | stable at both points, identical across all 3 runs each side |
| mixed | 8 | 7/8 (88%) | 7/8 (88%) | 0pp on the surface, see note below | single run each side, not yet repeated |
| groundedness | 2 | 2/2 | 2/2 | regression check only | n/a, zero model calls |
| topic_coverage | 2 | 2/2 | 2/2 | regression check only | n/a, zero model calls |
| resilience | 2 | 0/2 | 2/2 | regression check only | stable across all 3 runs at the current point |

Sources:
- `refund_evaluator`, `groundedness`, `topic_coverage`, `resilience` current: a live run today, `evals/results/20260822-201944` (commit `67509ca`, dataset version `78fcd15b208e`).
- `resilience` baseline, and `SQL / SQL semantic` and `rag` baseline and current: `evals/ablation_raw.json`, the `baseline` and `+ bounded failure handling` variants.
- `mixed` baseline: `evals/results/20260805-104832`. `mixed` current: the same live run above.

## Reading `mixed`'s unchanged number correctly

The rate held at 7/8 on both sides. The failing case changed.

Baseline, 2026-08-05, before the `DECISIONS.md` #46 prompt fix: `mixed-08` failed. The agent answered a refund-approval request and never stated it had no ability to approve one. Current, today, `mixed-08` passes. `mixed-07` fails instead, a new failure the judge caught: an answer that disputed a stated 236-day gap it should have confirmed against the real database rows.

The #46 fix held. A different, previously uncaught failure took its place.

## Why `SQL / SQL semantic` sits at n=7

This project treats 8 cases as the minimum before a percentage counts as real evidence (see `evals/results/baseline/report.md`). `refund_evaluator`, `rag`, and `mixed` all clear that bar. Combined, `sql` and `sql_semantic` land at 7 cases, one short of it.

I included this row anyway. Three runs of 7 cases each is 21 attempts on both sides, and a swing from 57 to 71 percent up to a stable 100 percent is too large a change to be random noise.

## `permission`, `prompt_injection`, `request_faithfulness`

All three of these categories sit at 100% today: `permission` 6/6, `prompt_injection` 5/5 runnable, `request_faithfulness` 6/6, all from the same fresh run. None of them has a real baseline to compare against, for three different reasons. `permission` was already at 6/6 back at the original baseline, so there's no change to show. `prompt_injection` and `request_faithfulness` didn't exist as runnable categories yet at that point. They stay out of the primary table above until there's an actual before-and-after story to tell.
