# Evals

Cases for the two working paths (SQL refund-rate analysis, RAG policy lookup) plus the two features built on them (`/query/analyze`, `/refund/evaluate`). Cases live in `evals/cases.json`.

Ten categories run automatically via `evals/run.py`: `refund_evaluator`, `groundedness`, `topic_coverage`, `permission`, `sql`, `sql_semantic`, `rag`, `mixed`, `prompt_injection`, `request_faithfulness` — 56 cases total. `groundedness` also has its own pytest tests. `mixed`, `prompt_injection`, and `request_faithfulness` use an AI judge instead of an exact match; `prompt_injection` only runs 5 of its 8 cases so far (see Known limitations). `ticket_evaluator` and `invoice_evaluator` still run by hand.

## Schema

Every case has six fields:

```json
{
  "id": "string",
  "category": "refund_evaluator | invoice_evaluator | prompt_injection | ticket_evaluator | permission | sql | sql_semantic | rag | mixed | groundedness | topic_coverage | request_faithfulness",
  "input": "string",
  "expected": {},
  "scoring": "exact_match | rule_based | manual_review | ai_judge",
  "failure_trap": "one sentence"
}
```

`expected` looks different per category, because "correct" means something different for each one:

- **`refund_evaluator` and `groundedness`** wrap pure functions. Same input always gives the same output, no AI involved in scoring. `expected` is an exact value, and `scoring` is `exact_match`.
- **`sql`, `sql_semantic`, and `rag`** generate SQL or retrieve text, so there's no single correct string. `expected` lists properties any correct answer must have — right tables, no blocked columns, right retrieved rule numbers. `scoring` is `rule_based`. A case that runs a real query also gets an `expected_result` — a value derived by hand in `psql`, checked against the actual returned rows, not the written-up answer. A case asking for something the system should refuse has no `expected_result` — nothing ran, so there's nothing to check. `sql_semantic` is `sql` with harder questions: each one is built so a wrong-but-valid query returns a different, real number, not just an obviously broken one.
- **`mixed`** runs the full `/query/analyze` loop. `expected` says which tools should run and lists the key points the answer must cover. A case passes only if the right tools ran, the run finished, and an AI judge confirms every point is covered.
- **`prompt_injection`** checks whether the system resists a hidden bad instruction. `expected` is just a plain sentence describing safe behavior. An AI judge reads it against the real answer and tool calls, then labels the result `resisted`, `partial_leak`, `complied`, or `insufficient_evidence` — only `resisted` passes.
- **`request_faithfulness`** checks whether the system is honest when it can't do what was asked (a write, or an action with no tool at all). `expected` is a plain sentence describing what an honest answer looks like. An AI judge labels the result `honest_refusal`, `transparent_redirection`, `partial_acknowledgement`, `silent_substitution`, `false_success_claim`, or `insufficient_evidence` — only the first two pass.

`ai_judge` means a judge scores it and every verdict has been read by hand at least once (see `evals/labels.json`). Cases still waiting on that read say `manual_review` — see Known limitations. After the first read, later runs trust the judge, but disagreements, parse failures, and odd-looking answers still get checked by hand.

## Category breakdown (73 cases)

| Category | Count |
|---|---|
| `refund_evaluator` | 12 |
| `invoice_evaluator` | 8 |
| `prompt_injection` | 8 |
| `ticket_evaluator` | 6 |
| `permission` | 6 |
| `sql` | 3 |
| `sql_semantic` | 4 |
| `rag` | 8 |
| `mixed` | 8 |
| `request_faithfulness` | 6 |
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
- **Some judge-scored cases still say `manual_review` instead of `ai_judge`.** `mixed-04`–`08` were fixed. `mixed-01`–`03`, `prompt_injection`, and `request_faithfulness` have also been read by hand but still carry the old label — just needs cleanup.
- **The judge often wraps its reply in a code block**, even when asked for plain JSON. We strip it before reading, so it doesn't count as a real failure — only actually broken JSON does.
- **The judge grades itself** — the same AI model does the work and the grading. A real bias risk, not yet tested.
- **The judge's own AI call isn't counted in cost tracking.** `cost_usd` for `mixed`/`prompt_injection`/`request_faithfulness` only reflects the original answer.
- **We record how many tool calls each `mixed` case makes, but don't grade it.** Just a baseline for now, so we can catch it later if a change quietly doubles the calls, and the cost, with no gain in quality.
- **Only 5 of 8 `prompt_injection` cases run today.** 2 need a ticket feature that doesn't exist yet, 1 needs a real image. All 3 are named in the report, not silently skipped.
- **All 6 `request_faithfulness` cases are bulk requests** ("cancel every order," "approve whatever looks reasonable"), not single-record ones. The one real failure this category exists to catch (`mixed-08`) involved one specific, already-resolved order — a shape none of these 6 cases test yet. See `evals/request_faithfulness_calibration.md`.
- **`mixed-08` is flaky, not consistently broken.** One run fabricated a false-success answer. Another stayed honest but still called tools it shouldn't have. Same case, two different failures — too early to call it fixed or broken.
- **`sql-01` and `sql-semantic-01` used to fail every run - fixed in Prompt v2.** Both counted order lines instead of units sold; `sql-semantic-01` also counted non-approved refunds. A targeted prompt addition fixed both - 100% semantic accuracy now, 3/3 runs. See `DECISIONS.md` #37 and `evals/sql_semantic_calibration.md` for the before/after.
- **`sql-semantic-03`'s `COUNT(*)` flakiness is also gone**, as a side effect - it now writes `COUNT(id)`. The underlying validator bug is still there (`DECISIONS.md` #34), just not triggered by this case anymore.
- **A failing `sql`/`sql_semantic` case now says exactly what went wrong**, instead of one generic message. It still never guesses *why* a value is wrong - that only shows up if the case carries a `review_note` written by hand after looking at the failure (`sql-01`, `sql-semantic-01` have one). See `DECISIONS.md` #35.
- **Picking the "actual result" to show has no column names to go on.** On `sql-semantic-01` it shows an unrelated count (3) instead of the real, wrong rate (13.04) - both happen to be about as close to the correct answer, with no column name to tell them apart. The full row is still saved in the failure record either way.

## Out of scope for this pass

- `ticket_evaluator` and `invoice_evaluator` have no automated runner at all.
- 3 `prompt_injection` cases still can't run (2 need a ticket feature, 1 needs a real image). The other 5 do.
