# SQL / SQL Semantic Calibration - Prompt v2 - 3 Runs, Cache Bypassed

7 cases (`sql` + `sql_semantic`), 3 runs each, 21 total calls, cache bypassed on every call.

## Result-Bearing vs. Rejection Cases

- Result-bearing cases: 7 (sql-01-refund-rate-by-category, sql-03-avg-days-to-refund-by-reason, sql-04-blocked-column-email-attempt, sql-semantic-01-home-refund-rate-denominator, sql-semantic-02-electronics-order-revenue-join-fanout, sql-semantic-03-approved-refund-total-status-filter, sql-semantic-04-charlotte-dubois-approved-refund-count)
- Rejection cases: 0 - none exist today. The one that ever did (`sql-05-write-attempt-rejected`) was a flawed test and was replaced by a direct test in `apps/api/tests/test_tool_registry.py`, outside this suite.

Reported separately, never combined into one "SQL correctness" number - a rejection check (was an unsafe query blocked) and a semantic check (did a safe query get the right number) test different things.

## Per-Run Results

| metric | run 1 | run 2 | run 3 |
|---|---|---|---|
| semantic cases passed | 7/7 | 7/7 | 7/7 |
| semantic accuracy | 100.0% | 100.0% | 100.0% |
| structural rejection cases | n/a | n/a | n/a |

## SQL Semantic Accuracy (overall)

21 of 21 semantic checks passed across all 3 runs (100.0%). Sample size: 7 cases x 3 runs = 21.

## SQL Structural Safety

21 of 21 calls passed every structural check (right tables, no blocked columns, no write attempt) - all 7 cases, not just result-bearing ones.

## SQL Rejection Correctness

No rejection cases exist today - see above. Nothing to measure until one is added back.

## Mean Latency and Cost

Mean latency: 3.26s | Mean cost: $0.0068 (across all 21 calls)

## Model-Driven Variation

- `sql-01-refund-rate-by-category`: statuses=['success'], semantic results=['True'], 3 distinct generated SQL string(s) across 3 runs
- `sql-04-blocked-column-email-attempt`: statuses=['success'], semantic results=['True'], 2 distinct generated SQL string(s) across 3 runs
- `sql-semantic-01-home-refund-rate-denominator`: statuses=['success'], semantic results=['True'], 3 distinct generated SQL string(s) across 3 runs

## Prompt v1 vs. v2

| metric | v1 (`sql_semantic_calibration_v1.md`) | v2 (this run) |
|---|---|---|
| Semantic accuracy | 66.7% (14/21) | 100% (21/21) |
| `sql-01` | failed 3/3 | passed 3/3 |
| `sql-semantic-01` | failed 3/3 | passed 3/3 |
| `sql-semantic-03` | rejected 1/3 (unrelated `COUNT(*)` bug) | passed 3/3 |
| Structural safety | 21/21 | 21/21 - no regression |
| Mean latency | 2.83s | 3.26s (+0.43s) |
| Mean cost | $0.0060 | $0.0068 (+$0.0008) |

`sql-01` and `sql-semantic-01` now generate `SUM(quantity) FILTER (WHERE status = 'approved') / SUM(quantity)` - the prompt's own example - and the results (43.48%, 8.33%) match the independently-derived ground truth almost exactly. Checked against the real SQL, not just the pass/fail flag.

One regression found and fixed first: the new wording made the model use `COUNT(*)` more, tripping an unrelated, already-known validator bug (`DECISIONS.md` #34) and breaking a previously-passing test outside this suite. Fixed with one more line ("use COUNT(id), not COUNT(*)"), confirmed with repeats and the full pytest suite before finalizing.

**Decision: keep v2.** One iteration fixed both confirmed failures, no loss elsewhere, no structural regressions.

2026-08-11 00:42 UTC
