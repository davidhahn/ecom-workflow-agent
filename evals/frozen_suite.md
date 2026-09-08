# Frozen Final Evaluation Suite

The reference dataset contains 79 cases. Individual runs and experiments use subsets of it. This report identifies those subsets and distinguishes historical results from comparisons made with the same cases.

## The frozen suite

- **Total cases:** 79
- **Cases by category:** refund_evaluator 12, rag 12, mixed 8, invoice_evaluator 8, prompt_injection 8, permission 6, request_faithfulness 6, ticket_evaluator 6, sql_semantic 4, sql 3, groundedness 2, resilience 2, topic_coverage 2
- **Dataset version:** `78fcd15b208e`, a short hash computed from the contents of `evals/cases.json`. `evals/run.py` calculates this same value and stamps it on every real run, so two runs with matching hashes ran against the identical case file.
- **Pinned to:** commit `06dbc8d` (2026-08-11, "Add retry logic to retryable failures"), the last commit that changed what's inside `cases.json`. This identifies the case file used by these reports.
- **Scorer version:** there's no separate version number for the scoring code, so the commit hash of `evals/run.py` stands in for one. `736c80c` is the reference commit recorded for this report.
- **Judge rubric version:** the same situation applies to the AI judge. `JUDGE_MODEL` (in `app/orchestrator/judge_client.py`) defaults to `claude-sonnet-4-6`, and its grading instructions live as plain prompt text inside `judge_answer()`, `judge_prompt_injection()`, and `judge_request_faithfulness()`, not as a separately versioned file. The reference point is `app/orchestrator/judge_client.py` at that same commit.

## Runnable coverage

`prompt_injection` has 8 cases written. Five ran in the saved August 22 snapshot. Two need a ticket draft/confirm harness, and one is an image-only invoice case unsupported by the text harness. Ticket drafting is implemented. The `ticket_evaluator` and `invoice_evaluator` categories also need draft/confirm harnesses. A pass rate for this category should read "5 of 5 runnable." Writing it as "5 of 8" makes the category look weaker than it is, unless a page is deliberately pointing at the coverage gap itself.

## What's already comparable, and why

Two experiment reports that already existed were checked against the frozen suite above, and both hold up without needing a rerun:

- **`evals/ablation_table.md`**: a frozen 27-case subset, run 3 times per variant, generated 2026-08-15. Its `resilience` column only became possible after the commit above, and its case list is a stable subset of the current 79 cases. It compares baseline, prompt v2, the retrieval threshold, bounded failure handling, and the Haiku model swap, all under the same questions and the same scorer, changing only one thing at a time.
- **`evals/model_comparison.md`** and **`evals/model_recommendation.md`**: a 46-case subset covering 8 of the 13 categories, generated 2026-08-17. `refund_evaluator`, `groundedness`, and `topic_coverage` are correctly left out, since none of the three ever calls a model, so a model comparison has nothing to compare there. I confirmed this subset draws on the same case IDs as the current suite.

These reports identify subsets of the reference dataset; their configurations and run counts still need to be read alongside each result.

**One coverage gap worth carrying into Findings:** the model comparison never touches `invoice_evaluator` or `ticket_evaluator`, 14 cases with no head-to-head Sonnet-versus-Haiku data at all.

## What's historical, not comparable, and has to be labeled that way

- **`evals/stability_check.md`**: 3 back-to-back runs, 38 total cases, generated 2026-08-03. This predates `resilience`, `sql_semantic`, `request_faithfulness`, `invoice_evaluator`, and `ticket_evaluator` entirely, and it still included `sql-05`, later removed as a flawed test case. Its headline number, 97.4%, describes a suite roughly half the size of the reference dataset. If the Evaluation Lab page ever cites this report for a run-to-run variance finding, it needs this label attached: "Historical result. Evaluation set changed after this run, and it isn't directly comparable with frozen-suite results."
- **`evals/results/baseline/`**: the very first full run this project ever recorded, from before the current suite existed, also including `sql-05`. This is a different artifact from the row labeled "baseline" inside `ablation_table.md`. That row is a separate, deliberately reconstructed old-code-state run, built by patching the current harness back to an earlier configuration (see `DECISIONS.md` #43) and running it against the current 27-case ablation subset. Two artifacts share the word "baseline," and only one of them, the ablation table's row, is comparable to the frozen suite.

## Calibration samples

`groundedness_calibration.md`, `rag_retrieval_calibration.md`, `sql_semantic_calibration.md`, and `request_faithfulness_calibration.md` aren't before-and-after system comparisons, so the "same frozen suite" rule above doesn't apply to them the same way. They test something else entirely: whether a heuristic, the groundedness check, the RAG threshold, the SQL scorer, the judge, agrees with a human label on a fixed sample. Where each of those samples came from belongs in `measurement_context.md`.
