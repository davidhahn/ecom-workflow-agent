# Architecture Critique

An independent review of this project's architecture, run as a cold read with no prior context on this codebase or its history — the brief given was to poke holes in it the way a skeptical senior engineer would before more gets built on top of it, not to summarize or rubber-stamp what's already documented.

**Method:** read `ARCHITECTURE.md`, `DECISIONS.md`, `PRODUCT_SPEC.md`, and `CLAUDE.md`, then cross-checked specific claims against the actual implementation under `apps/api/app/{orchestrator,query,rag,db}/` and the frontend, rather than taking the docs at their word. Findings are ranked by severity. The goal was findings beyond what `DECISIONS.md` already self-reports, not a restatement of its own tradeoffs.

The table below tracks what happened to each finding since. A fixed finding got a real code change, checked against a test or a measured number. An accepted finding is still real. I weighed what it would cost to fix against where this project stands, and chose to leave the risk in place on purpose. An open finding sits exactly where it started, and it carries real weight. Someone went looking for holes in this design without being told what they'd find. The table is what happened after that.

| # | finding | status | resolution / reasoning | evidence |
|---|---------|--------|-------------------------|----------|
| 1 | Groundedness check doesn't gate anything | accepted | Part 1 has no remediation flow. Hiding the answer had nowhere to go. A prominent warning banner makes the flag harder to miss now. | `DECISIONS.md` #18, commit `ec45312` |
| 2 | Refund resolution can match the wrong customer | fixed | `resolve_order_item()` refuses now when no customer identifier comes through, and returns `could_not_process`. | `DECISIONS.md` #16, commit `ec45312`, `test_evaluate_refund_request_returns_could_not_process_for_missing_customer` |
| 3 | No RAG relevance floor | fixed | A relevance threshold gates every RAG answer now, calibrated at 0.46 locally and 0.48 in production. One production-only ranking edge case remains, tracked as its own limitation. | `DECISIONS.md` #39, commits `bd56edf` + `4be52c1`, `evals/ablation_table.md` (off-topic refusal 0/15 → 12/15) |
| 4 | No semantic correctness check on the SQL path | fixed | `sql_semantic` checks the returned value now against a hand-verified number. The old check only looked at the query's shape. | `DECISIONS.md` #37, commit `0ed5da2`, `evals/sql_semantic_calibration.md` (66.7% → 100%, 3/3 runs) |
| 5 | Silent empty answer on tool-loop exhaustion | fixed | The loop returns an explicit `incomplete: True` now when Claude never reaches an answer. It used to fall through to an empty string that passed groundedness by accident. | `DECISIONS.md` #17, commit `ec45312`, `test_tool_loop_exhaustion_returns_incomplete_not_empty_grounded_answer` |
| 6 | Refund policy constants hand-duplicated, no drift protection | fixed | A test checks the evaluator's constants now against the actual wording in `refund_policy.md`. The numbers are still copied by hand. A mismatch fails that test today. | commit `1aab2ae`, `test_refund_policy_drift.py` (caught a real break during the `DECISIONS.md` #49 CI-gate test) |
| 7 | No timeout or retry on Anthropic calls | fixed | Every call gets a 30-second timeout and one bounded retry now, for timeouts, dropped connections, rate limits, and 5xx responses. | `DECISIONS.md` #38, commit `06dbc8d`, `test_two_retryable_failures_raises_with_retry_count_one` |
| 8 | Refund evaluator runs under the full-privilege connection | fixed | The evaluator runs under its own restricted `refund_evaluator_readonly` Postgres role now. | `DECISIONS.md` #29, commit `4e3d355`, `test_refund_evaluator_session_uses_restricted_readonly_role` |
| 9 | Partial-quantity refunds aren't modeled | open | `amount_cents` still uses the full line quantity. Extraction excludes quantity entirely, a side effect of a different fix. Nothing here has changed. | limitation, no fix scheduled |
| 10 | Zero authentication on any endpoint | accepted | Documented non-goal for Part 1 in `PRODUCT_SPEC.md`. Finding #2's fix narrows the risk this once compounded with. The gap itself hasn't moved. | `PRODUCT_SPEC.md`, README Limitations |

---

## High severity

**1. The groundedness check doesn't gate anything — it's a badge, not a backstop.**
`analyze_service.py` computes `grounded` / `ungrounded_claims` via `check_groundedness()`, but `AnalyzeResponse` always includes the LLM's full `answer` text regardless of the result. The frontend renders the complete answer with equal visual prominence to a small badge underneath. `ARCHITECTURE.md` describes this as one of two non-substitutable gates alongside the structural gate, but in practice only the structural gate actually stops anything from reaching the caller — the probabilistic check is pure telemetry. This directly undercuts the product promise (`PRODUCT_SPEC.md`: "trust the answer is... backed by an actual policy citation"): a support analyst under time pressure reading top-to-bottom could easily act on a flagged-but-still-displayed hallucination.

**Status: Accepted.** The frontend shows a prominent warning banner now, whenever `grounded` is false (`DECISIONS.md` #18). Before, a small badge did that job, easy to miss under time pressure. The answer still renders in full either way. Part 1 has no remediation flow, no re-generation, no escalation, so there was nowhere else for a flagged answer to go. The check still doesn't gate anything.

**2. Refund-request resolution can silently match the wrong customer, not just the wrong order.**
In `refund_evaluator.resolve_order_item()`, if `customer_identifier` is falsy (extraction returns an empty string whenever the request text doesn't name a customer — common, since Part 1 has no identity/session concept at all), the SQL applies **no customer filter whatsoever** and returns the single most-recent order_item matching the product name across the *entire* customer base. `DECISIONS.md` #11 only discusses ambiguity within one customer's multiple orders — it never surfaces that with no customer identifier, the evaluator can render a real approve/deny decision against a completely different customer's purchase history. This is a correctness gap in the core evaluated use case, undocumented anywhere.

**Status: Fixed.** `resolve_order_item()` refuses now when no customer identifier comes through. It used to fall back to a product-only match across every customer. A refund request naming no customer returns `could_not_process` (`DECISIONS.md` #16). Verified end to end against both seeded edge cases.

**3. No retrieval-relevance floor — groundedness verifies citation-vs-retrieved, never retrieved-vs-relevant.**
`rag/service.py::query_rag` always returns the top `k=3` chunks by cosine distance with no similarity threshold, out of a corpus of only ~17 chunks total. An off-topic or edge-case question still gets back its 3 "closest" chunks, and if the LLM cites one of them, `check_groundedness` passes trivially — it was retrieved, so it's "grounded," regardless of whether it's actually a good match for the question. This is precisely the gap-between-the-gates scenario the two-gate design is meant to close, but neither gate checks it: the structural gate has no visibility into RAG, and groundedness only checks presence, not relevance.

**Status: Fixed, with one open edge case.** A relevance threshold sits in front of every RAG answer now, calibrated at 0.46 locally and 0.48 in production (`DECISIONS.md` #39). A question with nothing relevant in the corpus gets refused. Before, it got a confident answer built on the closest available chunks anyway. One query, "damaged shipments policy," still ranks the wrong chunk first under the production embedding model. `DECISIONS.md` #53 and the README's Limitations section track that gap on its own, separate from the missing floor this finding named.

**4. No semantic/correctness check exists on the SQL path at all.**
The four layers (AST/table-column allowlist, cost, DB role, audit) validate *shape* and *permission* — none of them, nor anything else, checks whether the generated query's logic actually answers the question asked (wrong join, wrong denominator for a "rate," inverted filter). A structurally valid but semantically wrong query passes all four layers and gets confidently narrated in the final answer, with no counterpart to the RAG path's (weak, per #3) groundedness signal. This asymmetry between the two paths isn't self-reported anywhere.

**Status: Fixed.** A `sql_semantic` eval category checks the returned value now against a hand-verified number (`DECISIONS.md` #37). The old check only looked at the query's shape. The first real measurement came back at 66.7%. A targeted prompt fix brought that to 100%, holding across three runs since.

---

## Medium severity

**5. Silent empty-answer failure on tool-loop exhaustion — violates the project's own "Fail Loudly" rule.**
`analyze_service.py` runs `MAX_TOOL_ITERATIONS = 4`; if Claude is still requesting tools on the 4th call, the loop exits without ever hitting the `break` (which only fires when `stop_reason != "tool_use"`). `answer` then defaults to `""`, and since an empty string yields zero claimed citations, `check_groundedness("", ...)` trivially returns `grounded=True`. Net effect: a genuinely unanswered complex question renders as a blank answer with a green "Grounded" badge and a 200 OK — no error, no partial-result flag. `CLAUDE.md` explicitly names this exact pattern as a failure mode to avoid.

**Status: Fixed.** The loop returns an explicit `incomplete: True` now when Claude never reaches a final answer (`DECISIONS.md` #17). It used to fall through to an empty string. That path skips the groundedness check entirely, so an empty answer can't pass it by accident.

**6. Refund-policy numeric constants are hand-duplicated with zero drift protection — the opposite of the project's own stated principle.**
`refund_evaluator.py` hardcodes `REASON_WINDOW_DAYS`, `APPROVAL_THRESHOLD_CENTS`, `REPEAT_REFUND_THRESHOLD`, `FINAL_SALE_CATEGORIES`, etc., copied by hand from `docs/policies/refund_policy.md`. This is the exact anti-pattern the project explicitly engineered around elsewhere — decision #7's chunker and decision #9's groundedness rule-title map are both built to derive from the source doc rather than hand-duplicate it, specifically to avoid drift. Here, the numbers that actually drive real approve/deny/manager-approval decisions have no such linkage; a future policy edit (e.g. raising the threshold) silently desyncs with nothing to catch it.

**Status: Fixed.** `apps/api/tests/test_refund_policy_drift.py` checks the evaluator's hardcoded constants now against the actual wording in `refund_policy.md`. The numbers are still copied by hand, so this doesn't remove the duplication. A mismatch fails a test today, where it once shipped silently. The test already caught a real break, during a deliberate CI-gate check (`DECISIONS.md` #49).

**7. No timeout/retry/circuit-breaker on any Anthropic API call, on synchronous routes sharing one threadpool.**
`claude_client.py`, `refund_extraction.py`, and `analyze_service.py` all call the Anthropic SDK with default settings — no explicit timeout. Because the FastAPI routes are defined `def`, not `async def`, each call occupies a thread from FastAPI's shared, size-limited threadpool. A slow or rate-limited Anthropic API means hung requests accumulate across *all* request types at once — a spike of slow `/query/analyze` calls could starve unrelated `/refund/evaluate` calls. Not discussed anywhere in the docs.

**Status: Fixed.** Every Anthropic call now goes through a 30-second timeout and one bounded retry, with a 2-second delay, only for timeouts, dropped connections, rate limits, and 5xx responses (`DECISIONS.md` #38, `app/llm_retry.py`). A failed call returns a structured error instead of raising. `retry_count` on `request_log` records what happened, and a test mocks two failures in a row to confirm it.

**8. Refund evaluator's DB queries run under the full-privilege app connection, not the read-only role.**
`resolve_order_item` / `evaluate_refund` use `SessionLocal` (the same connection used for migrations/seeding), not `ops_agent_readonly`. These queries are partly built from LLM-extracted free text via `.ilike()` — parameterized, so no injection risk, but the same "assume the logic layer has bugs, keep an independent DB-level backstop" reasoning behind decisions #5/#6 was never applied to this second LLM-adjacent path.

**Status: Fixed.** The refund evaluator runs its queries now through its own restricted `refund_evaluator_readonly` Postgres role. That role is separate from the full-access connection used for migrations and seeding (`DECISIONS.md` #29). A test checks the evaluator is actually using it, so a regression here fails loudly.

**9. Partial-quantity refunds aren't modeled, despite the policy explicitly requiring proration.**
The refund-request extraction schema has no "how many units" field, and `evaluate_refund` always computes `amount_cents` as the full `quantity × unit_price_cents` for the line. A request to return 1 of 3 units gets evaluated as if the full 3-unit amount is being refunded, which can push a request across (or keep it under) the $200 manager-approval threshold incorrectly. `refund_policy.md`'s own "Partial Refunds" rule is simply unimplemented, and unlike the seed-date decay (#14) or ILIKE-ambiguity (#11) gaps, this isn't flagged anywhere as a known limitation.

**Status: Open.** `evaluate_refund()` still computes `amount_cents` as the full `quantity × unit_price_cents` for the line. Extraction still excludes quantity entirely. That change fixed a different bug, the "2 Ergonomic Desk Chairs" extraction case, and left this one alone. A request to return one of three units still gets evaluated as if the whole line is being refunded. Nothing has changed here since this finding was written.

---

## Low severity

**10. Zero authentication on any endpoint.**
No CORS middleware, no `Authorization`/API-key checks, no auth dependency anywhere in `apps/api/app`. Documented as a non-goal in `PRODUCT_SPEC.md`, but combined with finding #2, the actual risk is understated: anyone with network access can pull any customer's order/refund history and produce refund decisions against arbitrary identities, with no record of who asked. Fine for a localhost demo; the docs never caveat against pointing this at anything more reachable than that.

**Status: Accepted.** No authentication exists anywhere in the API. It's a documented non-goal, in `PRODUCT_SPEC.md` and in the README's own Limitations section. Finding #2's fix narrows the compounded risk this finding described. A wrong-customer decision can no longer happen silently. The underlying gap hasn't moved. Real deployment needs a real identity provider first.

---

## What held up well

Decision #6 (the column-grant vs. table-grant-then-revoke Postgres ACL discovery) is real, empirically-verified engineering — a genuinely non-obvious behavior (`REVOKE` on a column after a table-wide `GRANT` is a silent no-op) caught by actually testing it end-to-end, not just asserted in a comment, with the migration matching the doc's claim exactly. Decision #13 (`JSONB none_as_null`) is a sharp, non-obvious catch that most projects ship with silently. The named-citation groundedness heuristic (#9) and its explicit bias toward false positives over false negatives is a well-reasoned tradeoff given the stated constraint of no second LLM judge call — the reasoning holds up even under adversarial scrutiny, which is more than most self-reported tradeoffs survive.
