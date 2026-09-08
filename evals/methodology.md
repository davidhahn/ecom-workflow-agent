# Methodology Notes

Most cases use exact values or fixed scoring rules. Combined answers, prompt-injection responses, and unsupported-action responses use an LLM judge to assess the generated text.

## Judge Calibration

Three categories in this suite, `mixed`, `prompt_injection`, and `request_faithfulness`, can't be scored by an exact match. Whether an answer counts as correct depends on reading it, so a second AI model, the judge, reads the answer and grades it against a plain-language description of what a good one looks like. That only works if the judge itself is reliable, which is what this section checks.

```
LLM judge manually audited against human labels.
Disagreement: 0 / 33 cases (0%).
```

I compared 33 judge verdicts with human labels and found zero disagreements. All sampled outcomes were passes. This audit does not establish how reliably the judge recognizes failures or rejects correct answers.

## Repeated Runs

I repeated model-backed experiments to assess consistency across attempts. Each report states its run count.

`sql` and `sql_semantic` each ran 3 times in their own calibration, then 3 more times inside the ablation study, the experiment that compares different versions of the system side by side. `permission`, `prompt_injection`, `request_faithfulness`, `mixed`, `resilience`, `sql`, and `sql_semantic` each ran 3 times per model in the Sonnet-versus-Haiku comparison.

`rag` gets repeated for a different reason. `/query/rag` never calls a model at all, it only searches, so its 3 runs check something different: whether retrieval itself stays stable.

`mixed`'s current number, the one in `primary_results.md`, comes from a single live run. It hasn't been repeated yet. `DECISIONS.md` #46 already flagged this gap when the fix first shipped, and it's still open.

## Small-N Warning

These are portfolio-scale sets, 2 to 12 cases per category, small on purpose. They're built to answer one question: did a change make things better or worse. Read every percentage on this page that way. None of them is a claim about how the system performs across the much larger range of questions a real deployment would see.

## Reproduction Command

Run the supported categories with live model calls:

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
