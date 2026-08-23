# Methodology Notes

The rest of this page shows what the numbers are. This part is about how they were made. It's meant to take a reader from "these numbers look interesting" to "I understand where they came from."

## Judge Calibration

```
LLM judge manually audited against human labels.
Disagreement: 0 / 33 cases (0%).
```

That number is real. It's also narrower than it looks. All 33 sampled verdicts landed on a pass-shaped outcome: a plain `pass`, or a distinction between two good categories, `honest_refusal` and `transparent_redirection`. This calibration checks whether the judge is too lenient on those cases. It isn't. Two questions stay open. Would the judge catch a real failure? Would it ever punish a good answer unfairly? No `fail` verdict has been checked against a human read yet.

## Repeated Runs

`sql` and `sql_semantic` each ran 3 times in their own calibration, then 3 more times inside the ablation study. `permission`, `prompt_injection`, `request_faithfulness`, `mixed`, `resilience`, `sql`, and `sql_semantic` each ran 3 times per model in the Sonnet-versus-Haiku comparison.

`rag`'s repeated runs test something different. `/query/rag` never calls a model, so those 3 runs check whether retrieval itself stays stable.

`mixed`'s current number, the one in `primary_results.md`, comes from a single live run. It hasn't been repeated yet. `DECISIONS.md` #46 already flagged this gap when the fix first shipped, and it's still open.

## Small-N Warning

These are portfolio-scale sets, 2 to 12 cases per category, built for directional comparison and regression detection. Read a percentage here as "did this get better or worse." It isn't a claim about how the system performs across a broader population of real questions.

## Reproduction Command

Full suite, live model calls, the way it was run for this page:

```
cd apps/api
EVAL_RATE_LIMIT_BYPASS=1 poetry run python ../../evals/run.py --bypass-cache
```

Skipping `EVAL_RATE_LIMIT_BYPASS=1` breaks a full run. The suite shares one IP with real traffic, and `/query/analyze` and `/refund/evaluate` are both rate-limited.

Deterministic subset only, the one CI runs on every push, free and no API key needed:

```
cd apps/api
poetry run python ../../evals/run.py --subset deterministic
```
