# Evals

Eval cases for Part 1's two proven paths (SQL refund-rate analysis, RAG refund-policy lookup) plus the two orchestrator surfaces built on top of them (the combined `/query/analyze` path and `/refund/evaluate`). Cases live in `evals/cases.json`. No runner exists yet — this document describes the case set itself, not how it gets executed or scored (that's Part 4).

## Schema

Each case has the same six fields:

```json
{
  "id": "string",
  "category": "sql | rag | mixed | refund_evaluator | groundedness",
  "input": "string",
  "expected": {},
  "scoring": "exact_match | rule_based | manual_review",
  "failure_trap": "one sentence"
}
```

`expected` is deliberately not one fixed shape across categories — what counts as "correct" is different for each surface being tested:

- **`refund_evaluator` and `groundedness`** wrap pure, deterministic functions (`evaluate_refund()`, `check_groundedness()`). Given the same input, they return the same output every time, with no LLM judgment involved in scoring. `expected` is an exact literal (`{"status": ..., "rule_applied": ...}` / `{"grounded": ..., "ungrounded_claims": [...]}`), and `scoring` is `exact_match`.
- **`sql` and `rag`** test retrieval and query-generation, not prose. There's no single "correct" SQL string or "correct" wording for a retrieved chunk — many different queries or phrasings can be equally right. `expected` instead specifies structural properties that any correct answer must satisfy (tables joined, columns that must never appear, whether the request is a read-only-violation attempt; which `rule_number`(s) must appear in top-3 retrieval), and `scoring` is `rule_based`.
- **`mixed`** exercises the full `/query/analyze` orchestrator loop across both tools at once. There's no reliable automated way yet to score whether a free-text answer correctly combined a SQL result with a policy citation — that requires reading the answer. `expected` is a set of key points a correct answer should hit, and `scoring` is `manual_review`.

## Category breakdown (21 cases)

| Category | Count |
|---|---|
| `refund_evaluator` | 8 |
| `sql` | 4 |
| `rag` | 4 |
| `mixed` | 3 |
| `groundedness` | 2 |

`refund_evaluator` carries the most weight in the suite on purpose. It's the most deterministic, fully-testable surface in the whole system — a pure function over real seeded rows, with no LLM call in the scoring loop and no manual-review judgment call needed. Every other category either depends on LLM-generated SQL/prose (`sql`, `rag`, `mixed`) or on an LLM-generated answer being structurally checked (`groundedness`). Where a suite can lean on exact, cheap, deterministic assertions, it should — that's where the eval budget goes furthest.

## Design principle for `refund_evaluator` cases

Every `expected` value in this category was computed by tracing the actual rule text in `docs/policies/refund_policy.md` against actual rows in the seeded database — verified live via the read-only `/query/sql` endpoint, not hand-simulated from `seed.py`'s RNG-driven filler generation. No case describes a plausible-sounding scenario disconnected from a real row.

Cases were also deliberately chosen to cover **opposite-direction rule pairs**, not just one case per rule number. Rule 2 (`defective`) and rule 3 (`changed_mind`) both override the 30-day standard window, but in opposite directions off the same field (`requested_at - order_date`):

- Rule 2 **extends** the window to 90 days, and explicitly takes precedence over the 30-day standard when the two conflict.
- Rule 3 **contracts** the window to 14 days, shorter than the standard.

These are two different failure directions, not one concept tested twice. A bug that clamps every reason to a flat 30-day (or any single) window regardless of reason code, or that fails to apply rule 2's "takes precedence over standard" override specifically, would pass a suite that only tested one direction. `refund-04` (changed_mind, contraction) and `refund-05` (defective, extension) are both in the suite for this reason — cutting either one leaves the other direction's failure mode unguarded.

## Known limitations

Documented explicitly rather than left implicit:

- **Rule 6 (approval threshold, $200+) has no reachable eval case.** No seeded `order_item` exceeds $159.99 (`Ergonomic Desk Chair`, the highest-priced row in the dataset), and the refund-request extractor has no field for a customer-stated quantity override that could push a line total over the threshold. There is currently no way to construct a real, DB-grounded case that reaches this branch of `evaluate_refund()`.
- **Rule 7 (repeat-refund flag) has no reachable eval case, for a related but distinct reason.** The rule's 90-day lookback is computed against live `datetime.now()` at request time, while every seeded refund has a fixed historical `requested_at` anchored to `seed.py`'s `ANCHOR` date. As of this writing, no seeded refund falls within 90 days of "now" — the window has already rolled past all of them. This will get worse over time, not better, until seed dates are made relative to seed-time rather than fixed calendar dates (see `DECISIONS.md` #14).
- **`groundedness` cases don't fit the single-`input`-field schema cleanly.** `check_groundedness()` takes two arguments (`answer`, `retrieved_chunks`), not one. Both cases in this suite encode both as a single JSON-stringified object in the `input` field to stay within the given schema. Worth revisiting if Part 4's runner ends up needing more multi-argument cases like this — a stringified-JSON `input` is a workable stopgap, not a pattern to scale indefinitely.

## Out of scope for this pass

- No runner implemented (Part 4).
- No automated scoring for `mixed`/`manual_review` cases.
- No eval case for rules 6 or 7 until the gaps above are actually addressed (seed-data or extraction changes, not eval-authoring changes).
