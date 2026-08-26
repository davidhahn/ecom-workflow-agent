# Methodology Notes

The tables and reports elsewhere on this page show what the numbers are. This page is about how they were made, so a number here isn't something to just trust because it's sitting on a page.

## Judge Calibration

Three categories in this suite, `mixed`, `prompt_injection`, and `request_faithfulness`, can't be scored by an exact match. Whether an answer counts as correct depends on reading it, so a second AI model, the judge, reads the answer and grades it against a plain-language description of what a good one looks like. That only works if the judge itself is reliable, which is what this section checks.

```
LLM judge manually audited against human labels.
Disagreement: 0 / 33 cases (0%).
```

That number is real, and it's narrower than it looks. All 33 sampled verdicts landed on a pass-shaped outcome, a plain `pass`, or a distinction between two good categories, `honest_refusal` and `transparent_redirection`. So this calibration answers one specific question: is the judge too lenient on cases that already look fine? It isn't. Two harder questions stay open. Would the judge catch a real failure if one showed up? Would it ever punish a good answer unfairly? No `fail` verdict has been checked against a human read yet, so neither one is answered here.

## Repeated Runs

Model-backed categories don't give the same answer twice, since the model itself isn't deterministic. Running a category more than once is how I find out whether a passing result holds up, or whether it just got lucky that time.

`sql` and `sql_semantic` each ran 3 times in their own calibration, then 3 more times inside the ablation study, the experiment that compares different versions of the system side by side. `permission`, `prompt_injection`, `request_faithfulness`, `mixed`, `resilience`, `sql`, and `sql_semantic` each ran 3 times per model in the Sonnet-versus-Haiku comparison.

`rag` gets repeated for a different reason. `/query/rag` never calls a model at all, it only searches, so its 3 runs check something different: whether retrieval itself stays stable.

`mixed`'s current number, the one in `primary_results.md`, comes from a single live run. It hasn't been repeated yet. `DECISIONS.md` #46 already flagged this gap when the fix first shipped, and it's still open.

## Small-N Warning

These are portfolio-scale sets, 2 to 12 cases per category, small on purpose. They're built to answer one question: did a change make things better or worse. Read every percentage on this page that way. None of them is a claim about how the system performs across the much larger range of questions a real deployment would see.

## Reproduction Command

Full suite, live model calls, the way it was run for this page:

```
cd apps/api
EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --bypass-cache
```

Skipping `EVAL_RATE_LIMIT_BYPASS=1` breaks a full run. The suite shares one IP address with real traffic, and both `/query/analyze` and `/refund/evaluate` are rate-limited.

Deterministic subset only, the same one CI runs on every push, free and no API key needed:

```
cd apps/api
poetry run python ../../evals/run.py --subset deterministic
```
