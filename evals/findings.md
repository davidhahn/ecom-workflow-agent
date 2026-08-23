# Findings

Five investigations from the sprint, not a dashboard of every metric that moved. Each one starts with something that looked wrong and ends with what turned out to be true.

## Finding 1: The `sql-05` evaluation bug

`sql-05-write-attempt-rejected` asked the agent to update every pending refund to approved. The case expected a rejection. It failed instead, over and over.

Inspection showed why. Claude never attempted the write. It read the request, then ran an unrelated `SELECT` and answered with that. The case only checked one thing: did the response come back `rejected`. It couldn't tell the difference between two very different outcomes: the safety layer blocking an unsafe write, and the model quietly declining to write at all and doing something else instead. A pass or fail here proved nothing about whether the safety layer worked.

The case got removed. Its real claim, that a write attempt gets blocked, moved into a direct unit test of the validator instead (`apps/api/tests/test_tool_registry.py`), outside the eval suite. The application was never what needed fixing.

> I debug the measurement system as well as the model.

## Finding 2: Semantic correctness is a different question than safety

`sql-05`'s ambiguity pointed at something worth separating cleanly: whether a query is *safe* to run, and whether its *answer* is right, are two different questions. The SQL safety layer runs structural checks on tables, columns, and functions, and it never let anything unsafe through. Across 21 calls, 7 cases at 3 runs each, structural safety held 21 of 21 times.

Semantic correctness told a different story. New ground-truth assertions checked the returned value against a hand-derived expected number, not just the query's shape. They passed only 14 of 21 (66.7%).

The failures were specific. `sql-01`'s refund rate came back as refund records divided by order-item rows, 50.00%, every run, no matter how the query was worded. The correct figure, verified independently in `psql`, was 43.48%: refunded units over total units. One order line can hold more than one unit, so a row isn't a unit. `sql-semantic-01` made the same mistake and added a second one, counting a denied refund as if it had been paid. Both queries ran cleanly. Both passed every safety check. Both computed the wrong number, every run.

> Safety and correctness are different dimensions.

## Finding 3: Groundedness calibration

`check_groundedness()` is built to lean toward false positives on purpose, flagging a real citation as ungrounded rather than missing a fabricated one. That claim had never been measured. 20 answer and retrieved-chunk pairs, 12 pulled from real traffic and 8 written to target specific edge cases, got a human grounded/ungrounded label each, then ran through the real function.

```
TP: 2
FP: 5
FN: 2
TN: 11
n: 20
```

```
precision = 2 / 7  = 28.6%
recall    = 2 / 4  = 50.0%
false-positive rate = 5 / 16 = 31.2%
```

False positives outnumbered false negatives, 5 to 2, matching the design intent. One false negative stood out from the rest. An answer claimed a real, retrieved rule had been "waived." The heuristic passed it clean, because that rule's number was retrieved.

The check only confirms a number was present. It can't check whether the sentence around that number is true. Twenty pairs is a small sample, too small to say precisely how often that gap bites.

> I checked my own detector against real labels. Writing the heuristic doesn't make it correct.

## Finding 4: Cache-contamination audit

A model comparison depends on every run being a real, independent call. If two runs of the same question silently shared a cached answer, a quality difference between models could just be a caching artifact wearing a lie.

The audit checked whether that was happening. `evals/run.py` starts a fresh process every run, and the app cache is an in-memory dictionary scoped to that process, so a new run starts with nothing cached, structurally. `request_log` backed that up directly: 2,235 rows checked, and every repeated `sql`, `rag`, or `mixed` question came back with fresh tokens and fresh latency each time, never `cached: true`.

Nothing was contaminated here. The question was still worth asking twice. A related caching bug turned up later while building the ablation harness: `/query/rag`'s router had no `bypass_cache` field at all, and one variant's threshold effect was getting masked by another variant's cached answer. Every model-comparison run since bypasses cache explicitly. A process that happens to start clean is a weaker guarantee than a fresh call asked for directly.

> I looked for measurement contamination before interpreting model differences.

## Finding 5: Evaluation vs. production environment skew

This is the strongest finding in the sprint. It's the one that running the eval suite harder could never have caught.

Every eval in this project ran against local embeddings by default. Production runs a hosted provider instead, Voyage, because the local model's memory footprint didn't fit the deploy environment. Locally, the suggested question "What's our policy on damaged shipments?" retrieved the right policy chunk cleanly. Live, in production, the same question came back with a false "I don't know."

Tracing it down meant pulling the exact query Claude wrote for that request, `"damaged shipments policy"`, and running it against both providers directly. Same string, same corpus, opposite result.

Under local embeddings, the correct chunk ranked 2nd, distance 0.4191, comfortably inside the 0.46 threshold. Under Voyage, the same chunk ranked 4th, distance 0.6101, outside any cutoff that would still make sense. One fixed threshold couldn't serve both embedding spaces. `RELEVANCE_THRESHOLD` became a per-provider value, 0.46 local, 0.48 Voyage. That closed most of the gap.

Not all of it. The damaged-shipments case itself is still open. A real, on-topic chunk from a different policy document ranks ahead of the correct one under Voyage for this exact phrasing. Neither a tighter threshold nor a wider search fixed it without breaking something else. That stays a known limitation.

Testing the live app surfaced a second, unrelated bug. Extraction was folding a stated quantity into the product name: "2 Ergonomic Desk Chairs" instead of "Ergonomic Desk Chair," breaking the database match. The eval suite's refund cases feed pre-extracted fields straight into the rule engine and skip extraction entirely. The suite never runs extraction in its own fixtures, so it could never have caught this. That one got fixed and verified directly against the live endpoint.

> Offline evaluation catches real problems. Production behavior catches different ones. Both are evidence.
