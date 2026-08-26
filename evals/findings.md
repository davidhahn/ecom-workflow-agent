# Findings

This page collects five things I found while testing this project's evaluation suite. Some are bugs in the system I was testing. Others are bugs in the test itself, which is just as important to catch and easier to miss.

## Finding 1: The `sql-05` evaluation bug

The case `sql-05-write-attempt-rejected` asked the agent to approve every pending refund at once, a write the system should always refuse. The case expected that refusal and kept failing instead, every time it ran.

Looking closer showed why. Claude never tried the write at all. It read the request, ran an unrelated `SELECT` query instead, and answered with that. The case only checked one thing: did the response come back labeled `rejected`. That single check couldn't tell two very different outcomes apart: the safety layer catching a real write attempt, or the model quietly sidestepping the request and doing something else instead. A pass or a fail here said nothing about whether the safety layer worked.

I removed the case and moved its real claim, that a write attempt gets blocked, into a direct unit test of the validator (`apps/api/tests/test_tool_registry.py`), outside the eval suite entirely. The system was never what needed fixing.

> I debug the measurement system as well as the model.

## Finding 2: Semantic correctness is a different question than safety

The confusion in `sql-05` pointed at something worth separating cleanly. Whether a query is safe to run, and whether its answer is correct, are two different questions. The SQL safety layer runs structural checks on which tables, columns, and functions a query touches, and it never let anything unsafe through. Across 21 calls, 7 cases run 3 times each, structural safety held 21 of 21 times.

Semantic correctness looked different. The eval suite had only ever checked whether a query's shape looked right, the right tables, the right columns. It had never checked whether the number that came back was the actual right number. New assertions added exactly that: compare the returned value against one I worked out by hand in `psql`. They passed only 14 of 21 (66.7%).

The failures were specific. The `sql-01` case asks for a refund rate. Every run, the query divided the count of refund records by the count of order-item rows, and got 50.00%. The real number, checked independently in `psql`, is 43.48%: refunded units divided by total units sold. An order line can hold more than one unit, so a row isn't the same thing as a unit, and dividing by rows instead of units inflates the rate. `sql_semantic-01` made the same denominator mistake, and added a second one on top: it counted a denied refund as if it had been paid. Both queries ran without error, passed every safety check, and still computed the wrong number, every single run.

> Safety and correctness are different dimensions.

## Finding 3: Groundedness calibration

`check_groundedness()` is the function that checks whether a policy rule an answer cites was part of what got retrieved for that question, catching an answer that names a rule it never looked up. It's built to lean toward one kind of mistake on purpose: flagging a real, correct citation as ungrounded is an acceptable cost, and letting a made-up citation slip through as grounded is not. That design choice had never been measured, until now.

I built a set of 20 examples to check it: 12 pulled from real traffic, 8 written by hand to target specific edge cases. Each one got a human label, grounded or not, then ran through the real function to see whether it agreed.

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

False positives outnumbered false negatives 5 to 2, which is exactly what the design intended. One of the two false negatives is the more worrying kind. An answer claimed a real, correctly retrieved rule had been "waived," when nothing in the retrieved text said any such thing. The heuristic passed it clean, because the rule's number was retrieved. It never checked whether the claim about that rule was true.

The check only confirms a number was present. It has no way to check whether the sentence around that number is true. Twenty pairs is a small sample, too small to say exactly how often this happens in practice.

> I checked my own detector against real labels. Writing the heuristic doesn't make it correct.

## Finding 4: Cache-contamination audit

A model comparison only means something if every run is a real, independent call to the model. If two runs of the same question secretly reused a cached answer, a quality difference between two models could be nothing more than a caching artifact.

The audit checked whether that was happening. `evals/run.py` starts a brand new process for every run, and the app's cache lives only in that process's memory. When the process ends, the cache goes with it, so a new run always starts empty, guaranteed by how the process itself works. `request_log`, the database table that logs every real request the system handles, backed that up directly. I checked 2,235 rows: every repeated `sql`, `rag`, or `mixed` question came back with fresh token counts and fresh latency each time, never marked `cached: true`.

Nothing was contaminated here. The question was still worth asking twice. A related bug turned up later, while building the harness that compares different versions of the system against each other: the `/query/rag` endpoint had no way to skip its cache at all, so one version's results were quietly reusing another version's cached answer, hiding the actual effect being measured. Every model-comparison run since bypasses cache explicitly. A process that happens to start clean is a weaker guarantee than a fresh call asked for directly.

> I looked for measurement contamination before interpreting model differences.

## Finding 5: Evaluation vs. production environment skew

Of everything in this document, this is the finding I trust the most, because no amount of running the offline eval suite harder could have caught it.

Every eval in this project ran, by default, against a free embedding model on my own machine, the piece that turns policy text into searchable vectors for the RAG retrieval step. Production runs a different, hosted provider instead, called Voyage, because the local model's memory footprint was too big for the deploy environment. Locally, the question "What's our policy on damaged shipments?" retrieved the right policy chunk cleanly. Live, in production, the same question came back with a false "I don't know."

Tracing it down meant pulling the exact search query Claude generated for that request, `"damaged shipments policy"`, and running that same string against both providers, against the same corpus, to see what came back.

Under local embeddings, the correct chunk ranked 2nd, distance 0.4191, comfortably inside the 0.46 threshold. Under Voyage, the same chunk ranked 4th, distance 0.6101, outside any cutoff that would still make sense. One fixed threshold couldn't serve both embedding spaces. `RELEVANCE_THRESHOLD` became a per-provider value, 0.46 local, 0.48 Voyage. That closed most of the gap.

The damaged-shipments case itself is still open, one specific phrasing that still ranks the wrong chunk first under Voyage. A real, on-topic chunk from a different policy document ranks ahead of the correct one for this exact phrasing. I tried tightening the threshold and widening the search radius, and each fix broke something else. It stays a documented, open limitation.

Testing the live app surfaced a second, unrelated bug. The system that extracts fields from a free-text refund request was folding a stated quantity into the product name. "2 Ergonomic Desk Chairs" came out as the product name itself, and that string never matched the real product in the database, "Ergonomic Desk Chair." The eval suite's refund cases skip the extraction step. They feed already-extracted fields straight into the decision logic that approves or denies a refund, so the suite never runs extraction in its own fixtures and could never have caught this. That one got fixed and verified directly against the live endpoint.

> Offline evaluation and production behavior catch different problems, and I needed both to find everything in this document.
