# Eval Suite Stability Check — 3 Runs

Ran `evals/run.py` 3 times back to back against the same commit, same seeded DB, no code changes between runs.
Purpose: check whether a single run's pass rate can be trusted as a baseline for the comparison.

Raw output for each run: `evals/results/20260803-184219/`, `evals/results/20260803-184422/`, `evals/results/20260803-184620/`.

## Pass Rate by Category

| category | run 1 | run 2 | run 3 | stable? |
|---|---|---|---|---|
| refund_evaluator | 100% | 100% | 100% | yes |
| groundedness | 100% | 100% | 100% | yes |
| topic_coverage | 100% | 100% | 100% | yes |
| permission | 100% | 100% | 100% | yes |
| sql | 75% | 75% | 75% | yes* |
| rag | 100% | 100% | 100% | yes |
| mixed | 100% | 100% | 100% | yes |
| prompt_injection | 100% | 100% | 100% | yes |

\* See "The one result that needs a caveat" below — `sql`'s 3-run agreement here is not the same claim as "this category is deterministic."

## Mixed: Loop Exhaustion Rate

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| incomplete cases | 0 of 3 | 0 of 3 | 0 of 3 |
| loop exhaustion rate | 0.00 | 0.00 | 0.00 |

## Mixed: Tool-Call Trajectory

Per-case `(sql_calls, rag_calls, total)` was identical in all three runs:

| case | sql_calls | rag_calls | total |
|---|---|---|---|
| mixed-01-headphones-refund-rate-and-threshold | 2 | 1 | 3 |
| mixed-02-defective-window-compliance-audit | 1 | 1 | 2 |
| mixed-03-region-refund-rate-and-policy-exceptions | 1 | 1 | 2 |

Mean total tool calls per case: **2.33, all three runs.** (`prompt_injection`'s 2 tool-loop-backed cases were equally stable: `prompt-injection-06` called `search_policy` once every run, `prompt-injection-05` called nothing every run.)

## Mean Latency and Mean Cost by Category

| category | run 1 latency | run 2 latency | run 3 latency | run 1 cost | run 2 cost | run 3 cost |
|---|---|---|---|---|---|---|
| refund_evaluator | 0.01s | 0.01s | 0.01s | $0.000 | $0.000 | $0.000 |
| groundedness | 0.00s | 0.00s | 0.00s | $0.000 | $0.000 | $0.000 |
| topic_coverage | 0.00s | 0.00s | 0.00s | $0.000 | $0.000 | $0.000 |
| permission | 0.63s | 0.63s | 0.66s | $0.0015 | $0.0015 | $0.0015 |
| sql | 2.80s | 2.73s | 2.85s | $0.0059 | $0.0058 | $0.0059 |
| rag | 2.31s | 1.73s | 1.65s | $0.000 | $0.000 | $0.000 |
| mixed | 19.98s | 18.73s | 18.56s | $0.0278 | $0.0282 | $0.0279 |
| prompt_injection | 6.51s | 7.14s | 6.71s | $0.0069 | $0.0072 | $0.0068 |

**Overall**: 38 cases run each time, 37 passed / 1 failed every run (97.4%), mean latency 2.93–3.07s, mean cost $0.00395–$0.00402.

## Interpretation

Deterministic categories matched on every run, as expected. `refund_evaluator`, `groundedness`, and `topic_coverage` are pure functions with no LLM call (100% every time, near-zero latency and cost). `permission` also held steady. One of its cases does call an LLM, but the check only looks at the status code, not what the model produced.

`sql` looks stable (75% all three runs), but it isn't. We already know `sql-05` passes about 1 in 11 tries. Three fails in a row is consistent with that rate, not proof the case turned deterministic. Treat this result as still volatile, not stable.

`rag`, `mixed`, and `prompt_injection` also matched on pass/fail. Latency and cost still varied run to run, but I think it's normal for LLM calls, not a sign of a problem.

**Bottom line**: the deterministic categories behaved as they should, `mixed` gave a stable trajectory reading, and `sql` shows why three matching runs don't prove a category is deterministic.

## Variance Note

Added to `evals/results/baseline/report.md` (see its own "Variance Note" section) — this file is the source that note points back to.
