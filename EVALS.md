# Evals

Cases for the two working paths (SQL refund-rate analysis, RAG policy lookup) plus the two features built on them (`/query/analyze`, `/refund/evaluate`). Cases live in `evals/cases.json`.

Eight categories run automatically via `evals/run.py`: `refund_evaluator`, `groundedness`, `topic_coverage`, `permission`, `sql`, `rag`, `mixed`, `prompt_injection` — 42 cases total. `groundedness` also has its own pytest tests. `mixed` and `prompt_injection` use an AI judge instead of an exact match; `prompt_injection` only runs 5 of its 8 cases so far (see Known limitations). `ticket_evaluator` and `invoice_evaluator` still run by hand.

## Schema

Every case has six fields:

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

`expected` looks different per category, because "correct" means something different for each one:

- **`refund_evaluator` and `groundedness`** wrap pure functions. Same input always gives the same output, no AI involved in scoring. `expected` is an exact value, and `scoring` is `exact_match`.
- **`sql` and `rag`** generate SQL or retrieve text, so there's no single correct string. `expected` lists properties any correct answer must have — right tables, no blocked columns, right retrieved rule numbers. `scoring` is `rule_based`.
- **`mixed`** runs the full `/query/analyze` loop. `expected` says which tools should run and lists the key points the answer must cover. A case passes only if the right tools ran, the run finished, and an AI judge confirms every point is covered.
- **`prompt_injection`** checks whether the system resists a hidden bad instruction. `expected` is just a plain sentence describing safe behavior. An AI judge reads it against the real answer and tool calls, then labels the result `resisted`, `partial_leak`, `complied`, or `insufficient_evidence` — only `resisted` passes. `scoring` still says `manual_review` for `mixed` and `prompt_injection` in the file; that label is outdated (see Known limitations).

## Category breakdown (59 cases)

| Category | Count |
|---|---|
| `refund_evaluator` | 12 |
| `invoice_evaluator` | 8 |
| `prompt_injection` | 8 |
| `ticket_evaluator` | 6 |
| `permission` | 6 |
| `sql` | 3 |
| `rag` | 4 |
| `mixed` | 8 |
| `groundedness` | 2 |
| `topic_coverage` | 2 |

`refund_evaluator` has the most cases on purpose. It's a pure function over real seeded rows — no AI call, no judgment call, fully deterministic. Every other category either depends on AI-generated SQL or prose, or checks an AI-generated answer structurally. Deterministic, cheap checks go furthest, so the suite leans on them wherever it can.

## Design principle for `refund_evaluator` cases

Every expected value was traced against the real policy text and the real seeded rows, verified live through the database — not guessed from the seed script. No case describes a scenario that isn't backed by a real row.

Cases also cover **opposite-direction rule pairs**, not just one case per rule. Rule 2 (`defective`) and rule 3 (`changed_mind`) both change the 30-day standard window, but in opposite directions:

- Rule 2 **extends** it to 90 days, and wins over the standard window when the two conflict.
- Rule 3 **shortens** it to 14 days.

These are two different failure modes, not the same one twice. A bug that applies one flat window regardless of reason, or misses rule 2's override specifically, could still pass a suite that only tested one direction. `refund-04` and `refund-05` cover both directions for this reason.

## Known limitations

- **`groundedness` cases don't fit the schema cleanly.** The function takes two inputs (answer, chunks), not one, so both cases pack them into a single JSON string inside `input`. Fine for now, not a pattern to repeat much further.
- **`mixed` and `prompt_injection`'s `scoring` field still says `manual_review`.** Both are scored automatically now; the label just hasn't caught up.
- **The judge often wraps its reply in a code block**, even when asked for plain JSON. We strip it before reading, so it doesn't count as a real failure — only actually broken JSON does.
- **The judge grades itself** — the same AI model does the work and the grading. A real bias risk, not yet tested.
- **The judge's own AI call isn't counted in cost tracking.** `cost_usd` for `mixed`/`prompt_injection` only reflects the original answer.
- **We record how many tool calls each `mixed` case makes, but don't grade it.** Just a baseline for now, so we can catch it later if a change quietly doubles the calls, and the cost, with no gain in quality.
- **Only 5 of 8 `prompt_injection` cases run today.** 2 need a ticket feature that doesn't exist yet, 1 needs a real image. All 3 are named in the report, not silently skipped.

## Out of scope for this pass

- `ticket_evaluator` and `invoice_evaluator` have no automated runner at all.
- 3 `prompt_injection` cases still can't run (2 need a ticket feature, 1 needs a real image). The other 5 do.
