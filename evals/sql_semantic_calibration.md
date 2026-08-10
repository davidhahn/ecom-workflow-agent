# SQL / SQL Semantic Calibration - 3 Runs, Cache Bypassed

7 cases (`sql` + `sql_semantic`), 3 runs each, 21 total calls. `bypass_cache=true` on every call.

## Result-Bearing vs. Rejection Cases

- Result-bearing cases: 7 (sql-01-refund-rate-by-category, sql-03-avg-days-to-refund-by-reason, sql-04-blocked-column-email-attempt, sql-semantic-01-home-refund-rate-denominator, sql-semantic-02-electronics-order-revenue-join-fanout, sql-semantic-03-approved-refund-total-status-filter, sql-semantic-04-charlotte-dubois-approved-refund-count)
- Rejection cases: 0 - none exist today. The one that ever did (`sql-05-write-attempt-rejected`) was a flawed test and was replaced by a direct test in `apps/api/tests/test_tool_registry.py`, outside this suite.

Reported separately, never combined into one "SQL correctness" number - a rejection check (was an unsafe query blocked) and a semantic check (did a safe query get the right number) test different things.

## Per-Run Results

| metric | run 1 | run 2 | run 3 |
|---|---|---|---|
| semantic cases passed | 4/7 | 5/7 | 5/7 |
| semantic accuracy | 57.1% | 71.4% | 71.4% |
| structural rejection cases | n/a | n/a | n/a |

## SQL Semantic Accuracy (overall)

14 of 21 semantic checks passed across all 3 runs (66.7%). Sample size: 7 cases x 3 runs = 21.

## SQL Structural Safety

21 of 21 calls passed every structural check (right tables, no blocked columns, no write attempt) - all 7 cases, not just result-bearing ones.

## SQL Rejection Correctness

No rejection cases exist today - see above. Nothing to measure until one is added back.

## Mean Latency and Cost

Mean latency: 2.83s | Mean cost: $0.0060 (across all 21 calls)

## Model-Driven Variation

- `sql-01-refund-rate-by-category`: statuses=['success'], semantic results=['False'], 3 distinct generated SQL string(s) across 3 runs
- `sql-03-avg-days-to-refund-by-reason`: statuses=['success'], semantic results=['True'], 3 distinct generated SQL string(s) across 3 runs
- `sql-04-blocked-column-email-attempt`: statuses=['success'], semantic results=['True'], 2 distinct generated SQL string(s) across 3 runs
- `sql-semantic-01-home-refund-rate-denominator`: statuses=['success'], semantic results=['False'], 2 distinct generated SQL string(s) across 3 runs
- `sql-semantic-02-electronics-order-revenue-join-fanout`: statuses=['success'], semantic results=['True'], 2 distinct generated SQL string(s) across 3 runs
- `sql-semantic-03-approved-refund-total-status-filter`: statuses=['rejected', 'success'], semantic results=['None', 'True'], 2 distinct generated SQL string(s) across 3 runs

3 of the 4 cases with any variation still got the same pass/fail result every time - only the SQL's wording changed, not its logic. `sql-semantic-03` is the one where the outcome itself changed, and that's a separate app bug, not a reasoning difference - see below.

## Failure Investigation

Not fixing the prompt today. Each failure documented instead, so it's a measured target for later.

### `sql-01-refund-rate-by-category` — failed all 3 runs

- **Query generated**: all 3 computed `COUNT(DISTINCT r.id) / COUNT(DISTINCT oi.id) * 100` for Electronics. Wording changed run to run; the logic didn't.
- **Result returned**: 50.00% every time (10 refund records ÷ 20 order-item rows).
- **Wrong assumption**: "refund rate" read as refund records ÷ order-item rows, not units. Some order lines sell more than one unit, so a line isn't a unit. (The approved-only filter doesn't matter here - all 10 Electronics refunds are already approved - so this case only exposes the row-vs-unit half of the mistake.)
- **Was the expected value correct?** Yes - derived independently in `psql` (10 approved-refunded units ÷ 23 total units = 0.4348), checked against all 20 raw rows beforehand.
- **Stable across runs?** Yes - same wrong answer (50.00%) all 3 times, despite 3 differently-worded queries.

### `sql-semantic-01-home-refund-rate-denominator` — failed all 3 runs

- **Query generated**: same shape as `sql-01`, for Home. Same logic all 3 runs.
- **Result returned**: 13.04% every time (3 refund records ÷ 23 order-item rows).
- **Wrong assumption**: same row-vs-unit mistake, plus this case also catches a second one: refunds aren't filtered to `approved`, so a denied refund counts as if it were paid.
- **Was the expected value correct?** Yes - derived independently in `psql` (2 approved-refunded units ÷ 24 total units = 0.0833), checked against all 23 raw rows.
- **Stable across runs?** Yes - same wrong answer (13.04%) all 3 times.

### `sql-semantic-03-approved-refund-total-status-filter` — not a semantic failure

Rejected on run 1, passed clean on runs 2-3. Not the filter mistake this case was built to catch - the status filter was correct every time.

- **Query generated**: run 1 added a `COUNT(*)` column next to the `SUM(...)`; runs 2-3 only had the `SUM(...)`. All 3 correctly filtered `WHERE status = 'approved'`.
- **Result returned**: run 1 - none, rejected before running. Runs 2-3 - $1052.82, matching the independently-derived answer exactly.
- **Wrong assumption**: none - the logic was right every time it ran.
- **Was the expected value correct?** Yes, and beside the point - run 1 never got checked against it.
- **Stable across runs?** No - same logic runs or doesn't depending on whether the model happens to add a `COUNT(*)` column. That's the known `_check_no_select_star()` validator bug (`DECISIONS.md` #34), reconfirmed here, not a new one.

## Scorer or Fixture Problems Discovered

- **`COUNT(*)` validator bug** (already known) caused `sql-semantic-03`'s run 1 rejection. Not fixed here.
- **"Actual result" display limitation** (already known): `sql-semantic-01`'s failure shows `actual result: 3.0` (an unrelated count) instead of `13.04` (the real, wrong value) - `3` happens to be numerically closer to `0.0833` than `13.04` is, with no column name to tell them apart. Full row data is still saved in `sql_semantic_calibration_raw.json`.
- **No new scorer bugs.** Both issues above are re-occurrences of what was already documented, not new ones.

2026-08-10 01:05 UTC
