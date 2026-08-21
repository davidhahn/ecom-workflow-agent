# Frozen Final Evaluation Suite

The reference point for every comparison the Evaluation Lab page shows. Any number displayed as "current" or "final" on that page traces back to this exact case set. A historical number from a different case set gets labeled as historical, not placed next to these as if the denominator matched.

## The frozen suite

- **Total cases:** 79
- **Cases by category:** refund_evaluator 12, rag 12, mixed 8, invoice_evaluator 8, prompt_injection 8, permission 6, request_faithfulness 6, ticket_evaluator 6, sql_semantic 4, sql 3, groundedness 2, resilience 2, topic_coverage 2
- **Dataset version:** `78fcd15b208e`, the first 12 characters of a SHA-256 hash of `evals/cases.json`, the same `eval_dataset_version` value `evals/run.py` already computes and stamps on every real run
- **Pinned to:** commit `06dbc8d` (2026-08-11, "Add retry logic to retryable failures"), the last commit to change `cases.json`'s content. No content change since.
- **Scorer version:** no formal version constant exists for the scorer. `evals/run.py` at commit `736c80c` (current HEAD as of this writing) is the honest reference point, the same commit-as-proxy approach `run.py` already uses for `prompt_version`, since "no versioned prompt scheme exists yet" there either.
- **Judge rubric version:** same situation. `JUDGE_MODEL` (`app/orchestrator/judge_client.py`) defaults to `claude-sonnet-4-6`, and the rubric itself is prompt text inside `judge_answer()`, `judge_prompt_injection()`, and `judge_request_faithfulness()`, not a version-stamped artifact. Reference point: `app/orchestrator/judge_client.py` at the same HEAD.

## 79 cases exist. Fewer run today

`prompt_injection` carries 8 cases, but only 5 currently run: 2 need a ticket-drafting feature that isn't built yet, and 1 needs a real image. Any pass rate for this category should read "5 of 5 runnable," not "5 of 8," unless the page is deliberately showing the coverage gap itself.

## What's already comparable, and why

Two existing experiment reports were checked against the frozen suite above and hold up without a rerun:

- **`evals/ablation_table.md`**: a frozen 27-case subset, 3 runs per variant, generated 2026-08-15. Its `resilience` column exists, which only became possible after the 08-11 commit above. Its case list is a stable subset of the current 79. This is a clean same-questions, same-scorer, different-configuration comparison across baseline, prompt v2, retrieval threshold, bounded failure handling, and the Haiku model swap.
- **`evals/model_comparison.md`** and **`evals/model_recommendation.md`**: a 46-case subset (8 of the 13 categories; `refund_evaluator`, `groundedness`, and `topic_coverage` are correctly excluded since they never call a model), generated 2026-08-17. Confirmed to draw on the same case IDs as the current suite.

Neither needed a rerun. Both were already built the right way.

**Coverage gap worth carrying into Findings:** the model comparison never touches `invoice_evaluator` or `ticket_evaluator`, 14 cases with zero head-to-head Sonnet/Haiku data.

## What's historical, not comparable, and must be labeled that way

- **`evals/stability_check.md`**: 3 back-to-back runs, 38 total cases, generated 2026-08-03. This predates `resilience`, `sql_semantic`, `request_faithfulness`, `invoice_evaluator`, and `ticket_evaluator` entirely, and `sql-05` (later removed as a flawed test case) was still in the set. Its 97.4% headline number describes a suite roughly half the size of today's. If the Evaluation Lab page cites this report for its run-to-run variance finding, the citation needs: "Historical result. Evaluation set changed after this run; not directly comparable with frozen-suite results."
- **`evals/results/baseline/`**: the very first full run this project ever recorded, also from before the current suite existed, also including `sql-05`. This is a different artifact from the "baseline" row inside `ablation_table.md`. That row is a separate, deliberately reconstructed old-code-state run, built by patching the current harness back to an earlier configuration (see `DECISIONS.md` #43), executed against the current 27-case ablation subset. Same word, two different artifacts, and only one of them is comparable to the frozen suite: the ablation table's baseline row.

## Calibration studies use a different kind of ruler

`groundedness_calibration.md`, `rag_retrieval_calibration.md`, `sql_semantic_calibration.md`, and `request_faithfulness_calibration.md` aren't before-and-after system comparisons, so "same frozen suite" doesn't apply to them the same way. They test something else: whether a heuristic (the groundedness check, the RAG threshold, the SQL scorer, the judge) agrees with a human label on a fixed sample. Their own sample composition and provenance belong in the measurement-context part of this spec, not this freeze.
