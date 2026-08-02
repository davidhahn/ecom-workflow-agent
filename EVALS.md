# Evals

Eval cases for Part 1's two proven paths (SQL refund-rate analysis, RAG refund-policy lookup) plus the two orchestrator surfaces built on top of them (the combined `/query/analyze` path and `/refund/evaluate`). Cases live in `evals/cases.json`. Seven categories — `refund_evaluator`, `groundedness`, `topic_coverage`, `permission`, `sql`, `rag`, `mixed` (33 cases total) — run automatically via `evals/run.py`, which dispatches each case to the real function or live endpoint it tests (see `evals/README.md` for why the first four went first). The 2 `groundedness` cases are additionally wired into `apps/api/tests/test_groundedness_evals.py`, which parametrizes pytest over them and calls `check_groundedness()` directly. `mixed` is the newest one added: it checks whether the right tools ran, whether the run finished, and uses an AI judge to grade the answer against a checklist (see `mixed` under Schema below). The remaining 3 categories (`ticket_evaluator`, `invoice_evaluator`, `prompt_injection`) still have no automated runner and are checked by hand.

## Schema

Each case has the same six fields:

```json
{
  "id": "string",
  "category": "refund_evaluator | invoice_evaluator | prompt_injection | ticket_evaluator | permission | sql | rag | mixed | groundedness | topic_coverage",
  "input": "string",
  "expected": {},
  "scoring": "exact_match | rule_based | manual_review",
  "failure_trap": "one sentence"
}
```

`expected` is deliberately not one fixed shape across categories — what counts as "correct" is different for each surface being tested:

- **`refund_evaluator` and `groundedness`** wrap pure, deterministic functions (`evaluate_refund()`, `check_groundedness()`). Given the same input, they return the same output every time, with no LLM judgment involved in scoring. `expected` is an exact literal (`{"status": ..., "rule_applied": ...}` / `{"grounded": ..., "ungrounded_claims": [...]}`), and `scoring` is `exact_match`.
- **`sql` and `rag`** test retrieval and query-generation, not prose. There's no single "correct" SQL string or "correct" wording for a retrieved chunk — many different queries or phrasings can be equally right. `expected` instead specifies structural properties that any correct answer must satisfy (tables joined, columns that must never appear, whether the request is a read-only-violation attempt; which `rule_number`(s) must appear in top-3 retrieval), and `scoring` is `rule_based`.
- **`mixed`** exercises the full `/query/analyze` loop across both tools at once. `expected` says which tools should run (`expected_sql_used`, `expected_rag_used`) and lists `key_points` the answer should cover. A case passes only if the right tools ran, the run finished, and an AI judge confirms every key point is covered. Note: `scoring` still says `manual_review` in `cases.json` — that label is outdated now (see Known limitations).

## Category breakdown (55 cases)

| Category | Count |
|---|---|
| `refund_evaluator` | 12 |
| `invoice_evaluator` | 8 |
| `prompt_injection` | 8 |
| `ticket_evaluator` | 6 |
| `permission` | 6 |
| `sql` | 4 |
| `rag` | 4 |
| `mixed` | 3 |
| `groundedness` | 2 |
| `topic_coverage` | 2 |

`refund_evaluator` carries the most weight in the suite on purpose. It's the most deterministic, fully-testable surface in the whole system — a pure function over real seeded rows, with no LLM call in the scoring loop and no manual-review judgment call needed. Every other category either depends on LLM-generated SQL/prose (`sql`, `rag`, `mixed`) or on an LLM-generated answer being structurally checked (`groundedness`). Where a suite can lean on exact, cheap, deterministic assertions, it should — that's where the eval budget goes furthest.

## Design principle for `refund_evaluator` cases

Every `expected` value in this category was computed by tracing the actual rule text in `docs/policies/refund_policy.md` against actual rows in the seeded database — verified live via the read-only `/query/sql` endpoint, not hand-simulated from `seed.py`'s RNG-driven filler generation. No case describes a plausible-sounding scenario disconnected from a real row.

Cases were also deliberately chosen to cover **opposite-direction rule pairs**, not just one case per rule number. Rule 2 (`defective`) and rule 3 (`changed_mind`) both override the 30-day standard window, but in opposite directions off the same field (`requested_at - order_date`):

- Rule 2 **extends** the window to 90 days, and explicitly takes precedence over the 30-day standard when the two conflict.
- Rule 3 **contracts** the window to 14 days, shorter than the standard.

These are two different failure directions, not one concept tested twice. A bug that clamps every reason to a flat 30-day (or any single) window regardless of reason code, or that fails to apply rule 2's "takes precedence over standard" override specifically, would pass a suite that only tested one direction. `refund-04` (changed_mind, contraction) and `refund-05` (defective, extension) are both in the suite for this reason — cutting either one leaves the other direction's failure mode unguarded.

## Known limitations

Documented explicitly rather than left implicit:

- **`groundedness` cases don't fit the single-`input`-field schema cleanly.** `check_groundedness()` takes two arguments (`answer`, `retrieved_chunks`), not one. Both cases in this suite encode both as a single JSON-stringified object in the `input` field to stay within the given schema. Worth revisiting if Part 4's runner ends up needing more multi-argument cases like this — a stringified-JSON `input` is a workable stopgap, not a pattern to scale indefinitely.
- **`mixed`'s `scoring` field still says `manual_review`.** It's not manual anymore — `evals/run.py` now scores it automatically. The label just hasn't been renamed yet, since there's no good short name yet for "checks plus an AI judge."
- **The judge often wraps its reply in a `​```json` code block**, even though it's asked to return plain JSON. We strip that wrapper before reading the reply, so it doesn't count as a real parsing failure — only actually broken JSON does.
- **The judge uses the same AI model it's grading.** That's a real risk of bias we haven't tested for yet.
- **The judge's own AI call isn't included in cost tracking.** The `cost_usd` shown for `mixed` cases only counts the original answer, not the grading step.
- **We now record how many tool calls each `mixed` case makes, but don't grade it.** It's just a baseline for now, so we can notice later if a change quietly doubles the number of calls (and cost) without anyone meaning to.

## Out of scope for this pass

- `ticket_evaluator`, `invoice_evaluator`, and `prompt_injection` still have no automated runner. Everything else does now.
