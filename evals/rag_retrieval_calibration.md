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
