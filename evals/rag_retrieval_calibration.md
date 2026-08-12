# RAG Retrieval Calibration

What `/query/rag` and `/query/analyze` actually retrieve today, with a human relevance label on every chunk. Gives a future similarity or groundedness threshold real numbers to test against. Raw output: `evals/rag_retrieval_calibration_raw.json`.

## Method

The 12 `rag` cases in `evals/cases.json` (7 on-topic, 5 off-topic) were sent to `/query/rag` directly. The 6 `mixed` cases with `expected_rag_used: true` were sent to `/query/analyze` with `bypass_cache: true`, then the retrieved chunks were pulled from `/observability/requests`. This shows what the model itself searched for, not the raw question — `search_policy` runs on a model-written query, not the user's exact words.

Both runs used a freshly started API instance. The corpus is 21 chunks, not 17: `docs/notes/campaign-launch-notes.md` (4 chunks) is also in the RAG index, alongside the 3 policy docs, per `apps/api/app/rag/ingest.py`.

**Note:** a long-running dev server on port 8000 returned near-random similarities (0.02–0.08) and surfaced `campaign-launch-notes.md` chunks even for clearly policy-related questions — well off from every existing case's documented numbers. That instance was not used for this calibration. Worth a separate look — it suggests that server's query embeddings no longer match what's stored in `policy_chunks`.

`distance` is cosine distance (`1 - similarity`) — the same ordering `/query/rag` already returns.

## Cases

| case | question | search_policy query (mixed only) |
|---|---|---|
| rag-01 | What's the default return window for a purchase if there's nothing special about the situation? | — |
| rag-03 | Does anything special happen if a customer keeps returning things over and over? | — |
| rag-04 | If I only return 2 of the 3 units I bought on one order line, how is my refund amount calculated? | — |
| rag-05 | Do you refund what I paid for shipping when I return an item? | — |
| rag-06 | Is there a dollar amount above which a refund needs manager sign-off? | — |
| rag-07 | I grabbed a marked-down item off your clearance rack last week and just don't want it anymore - can I get my money back for that one, or are those handled differently? | — |
| rag-08 | This product broke down after a few uses, and honestly I don't want it anymore either - how much time do I have to send it back? | — |
| rag-09 | Do you offer any kind of loyalty rewards program for customers who order frequently? | — |
| rag-10 | What is your gift card balance and expiration policy? | — |
| rag-11 | Do you offer price matching or price adjustments if an item goes on sale after I buy it? | — |
| rag-12 | What are the customs duties or import taxes on an international order? | — |
| rag-13 | Can I cancel my order before it ships? | — |
| mixed-01 | We've seen a lot of refund requests for the Bluetooth Headphones Pro. What's its refund rate, and would any of those refund amounts have required manager approval under our policy? | manager approval required refund amount threshold |
| mixed-02 | Are we correctly enforcing the 90-day defective-item return window? Show me any approved defective refunds that were requested more than 90 days after the order date. | defective item return window 90 days refund policy |
| mixed-03 | Which customer regions have the highest refund rates, and does our refund policy carve out any exceptions by region? | regional exceptions refund policy by region |
| mixed-04 | Which customers currently qualify for our repeat-refund flag, and how many qualifying refunds does each have? | repeat refund flag qualification criteria |
| mixed-06 | What does our policy require before a damaged-shipping refund can be processed? | damaged shipping refund requirements |
| mixed-07 | Charlotte Dubois filed a refund for her Wireless Keyboard 236 days after she placed the order, citing that she received the wrong item, and it was approved. Does that comply with our return-window policy? | return window refund eligibility wrong item received |

## Results

| case | rule | rank | distance | relevant? |
|---|---|---|---|---|
| rag-01 | 1 (Standard Return Window) | 1 | 0.342 | yes |
| rag-01 | 9 (Final-Sale Exclusion) | 2 | 0.441 | no |
| rag-01 | 7 (Repeat-Refund Flag) | 3 | 0.444 | no |
| rag-03 | 7 (Repeat-Refund Flag) | 1 | 0.455 | yes |
| rag-03 | 5 (Wrong Item Shipped) | 2 | 0.489 | no |
| rag-03 | 1 (Standard Return Window) | 3 | 0.490 | no |
| rag-04 | 8 (Partial Refunds) | 1 | 0.286 | yes |
| rag-04 | 6 (Approval Threshold) | 2 | 0.386 | no |
| rag-04 | 7 (Repeat-Refund Flag) | 3 | 0.388 | no |
| rag-05 | 10 (Shipping Cost Non-Refundable) | 1 | 0.298 | yes |
| rag-05 | 5 (Wrong Item Shipped) | 2 | 0.358 | maybe |
| rag-05 | 4 (Damaged in Shipping) | 3 | 0.363 | maybe |
| rag-06 | 6 (Approval Threshold) | 1 | 0.250 | yes |
| rag-06 | 7 (Repeat-Refund Flag) | 2 | 0.372 | no |
| rag-06 | 3 (Changed Mind) | 3 | 0.462 | no |
| rag-07 | 9 (Final-Sale Exclusion) | 1 | 0.397 | yes |
| rag-07 | 3 (Changed Mind) | 2 | 0.408 | maybe |
| rag-07 | 1 (Standard Return Window) | 3 | 0.411 | no |
| rag-08 | 1 (Standard Return Window) | 1 | 0.360 | maybe |
| rag-08 | 2 (Defective Items) | 2 | 0.366 | yes |
| rag-08 | 3 (Changed Mind) | 3 | 0.370 | maybe |
| rag-09 | 7 (Repeat-Refund Flag) | 1 | 0.524 | no |
| rag-09 | none (Standard Shipping) | 2 | 0.545 | no |
| rag-09 | none (Expedited Shipping) | 3 | 0.557 | no |
| rag-10 | 3 (Changed Mind) | 1 | 0.506 | no |
| rag-10 | 9 (Final-Sale Exclusion) | 2 | 0.514 | no |
| rag-10 | 1 (Standard Return Window) | 3 | 0.534 | no |
| rag-11 | 9 (Final-Sale Exclusion) | 1 | 0.482 | no |
| rag-11 | 3 (Changed Mind) | 2 | 0.517 | no |
| rag-11 | 1 (Standard Return Window) | 3 | 0.525 | no |
| rag-12 | none (Expedited Shipping) | 1 | 0.487 | no |
| rag-12 | none (Standard Shipping) | 2 | 0.493 | no |
| rag-12 | 10 (Shipping Cost Non-Refundable) | 3 | 0.499 | no |
| rag-13 | none (Damaged in Transit) | 1 | 0.425 | no |
| rag-13 | 4 (Damaged in Shipping) | 2 | 0.426 | no |
| rag-13 | 5 (Wrong Item Shipped) | 3 | 0.429 | no |
| mixed-01 | 6 (Approval Threshold) | 1 | 0.185 | yes |
| mixed-01 | 7 (Repeat-Refund Flag) | 2 | 0.435 | no |
| mixed-01 | 3 (Changed Mind) | 3 | 0.484 | no |
| mixed-02 | 2 (Defective Items) | 1 | 0.240 | yes |
| mixed-02 | 9 (Final-Sale Exclusion) | 2 | 0.373 | no |
| mixed-02 | 1 (Standard Return Window) | 3 | 0.395 | maybe |
| mixed-03 | 6 (Approval Threshold) | 1 | 0.465 | no |
| mixed-03 | 9 (Final-Sale Exclusion) | 2 | 0.467 | no |
| mixed-03 | 10 (Shipping Cost Non-Refundable) | 3 | 0.494 | no |
| mixed-04 | 7 (Repeat-Refund Flag) | 1 | 0.325 | yes |
| mixed-04 | 6 (Approval Threshold) | 2 | 0.379 | no |
| mixed-04 | 9 (Final-Sale Exclusion) | 3 | 0.472 | no |
| mixed-06 | 4 (Damaged in Shipping) | 1 | 0.288 | yes |
| mixed-06 | none (Damaged in Transit) | 2 | 0.288 | yes |
| mixed-06 | 10 (Shipping Cost Non-Refundable) | 3 | 0.352 | maybe |
| mixed-07 | 2 (Defective Items) | 1 | 0.288 | no |
| mixed-07 | 5 (Wrong Item Shipped) | 2 | 0.299 | yes |
| mixed-07 | 1 (Standard Return Window) | 3 | 0.329 | no |

## Reading the numbers

- The correct rule lands at rank 1 with distance ≤ 0.40 for every on-topic case, except rag-08. There, rule 1 beats the correct rule 2 by a hair (0.360 vs. 0.366) — a near-tie built into the case on purpose (see its `failure_trap`). mixed-01 is the tightest match in the whole set at 0.185.
- Every off-topic case (rag-09 through rag-13) stays at distance ≥ 0.40 with no `yes` or `maybe` labels — the corpus really has nothing for these.
- mixed-03 is the one case with no `maybe` at all: the policy has no region-based rule, so all three retrieved chunks are equally beside the point.
- `maybe` marks a chunk that's a real, policy-connected exception or cross-reference (e.g. rag-05's rules 4/5, mixed-06's rule 10), not a coincidental word match. Off-topic cases never reach that bar.

## Threshold Selection

Based on the `yes` (13 rows) and `no` (34 rows) labels above. `maybe` (7 rows) is left out since it's not clearly one or the other.

- **Highest distance among clearly relevant examples:** 0.455 — rag-03, rule 7 (Repeat-Refund Flag).
- **Lowest distance among clearly irrelevant examples:** 0.288 — mixed-07, rule 2 (Defective Items), rank 1.

**Overlap:** quite substantial. `yes` ranges `[0.185, 0.455]`, `no` ranges `[0.288, 0.557]`. They overlap across `[0.288, 0.455]` (most of the `yes` range). 9 of 13 `yes` examples fall in that band, and so do 14 of 34 `no` examples. Clearest example: for mixed-07, the correct chunk (rule 5, distance 0.299) ranks *behind* a wrong one (rule 2, distance 0.288), so it seems that distance alone doesn't cleanly tell relevant from irrelevant here.

**Threshold: 0.46** (0.455 rounded up). The strictest value that still keeps every relevant example in this set. 14 of 34 irrelevant examples still fall under it and would count as relevant, so it doesn't fix the overlap. Going stricter would start rejecting correct rules too (rag-03 first, then rag-07 at 0.397, rag-08 at 0.366), which we want to avoid.

**Small sample:** 13 `yes` + 34 `no` labels from 18 questions. Enough to rule out a bad threshold, but not enough to tune a precise one. Treat 0.46 as a starting point, not a final value. Should be revisited once real `/query/analyze` traffic gives a bigger sample.

## Post-Threshold Rerun

The 0.46 cutoff now lives in `query_rag()`. I reran the same 18 questions against a fresh instance. The 12 `rag` cases went straight through `/query/rag`. The 6 `mixed` cases went through `/query/analyze` with `bypass_cache: true`.

| metric | before | after |
|---|---|---|
| off-topic refusal rate (5 cases) | 0/5 | 4/5 |
| on-topic expected-rule retrieval (12 cases) | 12/12 | 12/12 |

Four off-topic cases come back empty now. rag-09, rag-10, rag-11, and rag-12 all return zero chunks and the explicit message. rag-13 does not. Its three chunks sit at 0.425 to 0.429, just under the cutoff, so the question still reads as answerable. This is the gap the calibration table already flagged.

Every on-topic case kept its correct rule. rag-03 came back with one chunk instead of three. The other two were noise anyway, so nothing useful got dropped.

mixed-03: no rule in the policy governs regional exceptions, so it never had a real answer to retrieve. It used to come back with three unrelated rules as padding. Now it comes back empty, and the model says plainly that no policy covers this.

One separate thing turned up: mixed-01 came back `grounded: false` this run. Retrieval was fine. Rule 6 landed first, at distance 0.185. The flag came from a data table in the answer that listed a refund reason as "Damaged in shipping," which happens to match rule 4's title word for word. That's a known quirk in `check_groundedness()`, already written up in `DECISIONS.md` #32 and `evals/groundedness_calibration.md`. It has nothing to do with this threshold.

The threshold rejects irrelevant evidence in four of five off-topic cases. It costs nothing on the on-topic side. rag-13 stays open, the known price of a cutoff built to protect recall first.

Raw output: `evals/rag_retrieval_calibration_raw.json`, `post_threshold_rerun` key.
