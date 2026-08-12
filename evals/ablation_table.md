# System Evolution: Ablation / Experiment Table

Every row here is a real change, listed in the order it happened, sourced from a real report or calibration file. A column a change didn't touch just says so. No number here was invented. Each row's source has the full method.

## Table

| variant | semantic SQL | off-topic refusal | on-topic RAG | latency | cost | decision |
|---|---|---|---|---|---|---|
| baseline | not measurable yet (structural only) | n/a (no off-topic cases existed) | 100% (4/4, n too small to trust) | 0.72s (whole-suite mean) | $0.001 (whole-suite mean) | reference |
| remove sql-05 issue | not measurable yet (structural only) | n/a | unchanged | unchanged (query generation untouched) | unchanged | keep |
| + semantic assertions | 66.7% (14/21), newly measurable, exposes a real row-vs-unit bug | n/a | unchanged | 2.83s (sql/sql_semantic mean) | $0.0060 | measurement only |
| + prompt v2 | 100% (21/21), up from 66.7% | 0/1 (only rag-09 existed, no threshold yet) | unchanged | 3.26s (+0.43s) | $0.0068 (+$0.0008) | keep |
| + retrieval threshold | unchanged (100%) | 0/5 to 4/5 (80%) | 12/12 (100%, preserved) | unchanged (rag has no LLM call) | unchanged ($0, embedding-only) | keep (rag-13 is a known, documented gap) |
| + bounded failure handling | unchanged (100%, normal-case path untouched) | unchanged (4/5) | unchanged (12/12) | unchanged in the normal case (0 retries fire when calls succeed) | unchanged in the normal case | reliability invariant |

## What each row is, and its source

- **baseline**: `evals/results/baseline/report.md`, 2026-08-01. This predates `mixed` and `prompt_injection`. `sql` shows 75% (3/4) here only because `sql-05` was flaky. Its true pass rate was closer to 1 in 11. See `evals/stability_check.md`.
- **remove sql-05 issue**: 2026-08-04. `sql-05` tested two things at once, "did Claude try to write" and "did the safety layer block it," so a failure couldn't say which broke. A direct test in `apps/api/tests/test_tool_registry.py` replaced it. The test changed. SQL generation stayed the same. Full history sits in `evals/failure_taxonomy_review.md`.
- **+ semantic assertions**: `DECISIONS.md` #33-#35, 2026-08-08 to 09. The `sql` and `sql_semantic` cases gained a real expected value, checked in `psql`. Before this, they only checked query shape. Nothing about SQL generation changed that day. A bug that had always been there, refund rate computed as rows instead of units, simply became visible. 66.7% comes from `evals/sql_semantic_calibration_v1.md`, run right before prompt v2.
- **+ prompt v2**: `DECISIONS.md` #37, 2026-08-10. One paragraph and a worked example, added to the SQL prompt, nothing else. `evals/sql_semantic_calibration.md` has the full before-and-after: both confirmed bugs fixed, an incidental `COUNT(*)` validator trip fixed along the way, no structural regression across 21 calls. Off-topic refusal shows 0/1 here, since only `rag-09` existed and no threshold existed yet to reject anything.
- **+ retrieval threshold**: `DECISIONS.md` #39, `evals/rag_retrieval_calibration.md`, 2026-08-10 to 11. `RELEVANCE_THRESHOLD = 0.46` in `app/rag/service.py` came from 54 hand-labeled chunks across 18 questions. It's the tightest cutoff that still kept every clearly-relevant one. Off-topic and on-topic numbers here are from a real rerun of the same 18 questions, before the change and after.
- **+ bounded failure handling**: `DECISIONS.md` #38, 2026-08-11. One retry, a 30-second timeout, on the SQL and analyze paths. This row stays flat everywhere a normal, successful call gets measured. That's on purpose. It's about what happens when a call fails. Two new `resilience` cases measure that directly: they mock two failures in a row and check for a structured failure, a `retry_count` of 1, and no fabricated data. See the `resilience` category in `evals/run.py`.

## Reading this table

Most rows leave most columns alone. `+ semantic assertions` changed nothing about the system. It changed what could be seen. `+ prompt v2` is the only row that changed SQL output. `+ retrieval threshold` is the only row that changed retrieval, and it comes with a real cost: `rag-13`. `+ bounded failure handling` sits flat across every quality column on purpose. It's a reliability invariant, checked by a separate pair of cases built to fail. A number in every cell would misrepresent what these changes do.

## Full-suite confirmation

The whole suite ran at the current state, with every row above applied. Full report: `evals/results/20260812-101041/report.md`.

62 cases ran. 61 passed, 1 failed, 98%. Mean latency came to 4.71s, mean cost to $0.005. The one failure is `mixed-08-refusal-to-execute-refund`, the same write-substitution issue first found in `evals/error_analysis_report.md`. It's still open. This session didn't touch it either way.

Two things stand out:

- `rag` now shows 12/12, 100%, covering all 7 on-topic and all 5 off-topic cases. That number doesn't settle whether off-topic refusal works. The scoring only checks whether the expected rule came back, and an off-topic case's expected rule list is empty. So it passes whether the corpus correctly returns nothing, or whether it returns something wrong, the way `rag-13` does. The real off-topic number is the 4/5 further up, not this 12/12.
- `resilience` showed up in a full-suite report for the first time: 2/2, 0.03s mean latency, $0 cost. Both cases mock the failure and never touch the real API. The retry path holds inside the full harness, the same as it does in pytest alone.
