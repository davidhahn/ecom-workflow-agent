# Evals

A quick look at each category in `evals/cases.json`: what it checks, why it can be scored automatically, and what a failure means.

## `refund_evaluator`

The category with the most cases (12), since it deals with financial data. Each case feeds a real order into `evaluate_refund()` and checks two things: the right outcome, and the right policy rule cited. It's a pure function with no AI in the decision, so the expected value can be traced exactly against real data. A failure here means the system told a customer the wrong thing.

## `groundedness`

Two cases test whether `check_groundedness()` itself still works — not whether the app's answers are generally grounded. The function flags an answer that cites a policy rule that was never retrieved; these cases confirm that detection still fires. Both feed a fixed answer and fixed chunks directly into the function, so scoring is exact. A failure here means a hallucinated rule could drive a real refund decision.

## `topic_coverage`

A second, independent guard for a different failure mode: does an answer make shipment claims when no shipment data was ever queried. Same as `groundedness`, it's a deterministic check on a fixed answer and a fixed record of what was queried. A failure here means the system stated something about a shipment with nothing backing it up.

## `permission`

More of an integration test than a model eval. These six cases confirm a role either gets to call an endpoint or gets a 403, matching the tool registry. Example: a support agent can draft a ticket but not confirm one. Scoring is exact — it's a status code check. A failure here isn't a quality miss, it's an access-control hole.

## Why these four first

None of these four measure AI quality. They should score at or near 100%, by design. No model calls, no cost, no variance, known outcomes — they're the control group that proves the harness and reporting work before pointing any of it at real, noisy model behavior. A failure here means a bug in the code or the test data, not the model.

## `sql`

The first category that actually calls the model. Each case sends a question to `/query/sql` and checks the SQL it generates — right tables, no blocked columns, right status. There's no single correct SQL string, so scoring checks for the right pieces of text, not an exact match. A failure means the generated SQL got the wrong answer or leaked a column it shouldn't have.

**Known limitation:** this is text matching, not real SQL parsing. A table joined through an alias could look like a miss; a name inside a comment or string could look like a hit. A first pass, not a full solution.

## `rag`

Each case sends a question to `/query/rag` and checks whether the right policy rule shows up in the retrieved chunks. No AI call here — just embedding + similarity search — so results are stable run to run, unlike `sql`.

**Known limitation:** this only measures recall — did the right rule come back. It doesn't check whether irrelevant chunks also came back, or whether an answer would actually use the rule correctly.

## `mixed`

Runs the full `/query/analyze` loop and checks it a few ways: did it call the right tools, did it finish instead of hitting the loop limit, and does an AI judge confirm the answer covers every required point. Unlike the categories above, part of the grading is a judgment call, not a fixed rule. A failure means the system routed to the wrong tool, gave an incomplete answer, or missed something it needed to say.

## `prompt_injection`

Sends a message with a hidden bad instruction and checks whether the system falls for it. An AI judge reads the real answer and tool calls, then labels the result `resisted`, `partial_leak`, `complied`, or `insufficient_evidence` — only `resisted` passes. Same as `mixed`, this needs a judge, not a fixed rule. A failure means a hidden instruction actually changed the system's behavior.

**Known limitation:** only 5 of 8 cases run today. 2 need a ticket feature that doesn't exist yet, 1 needs a real image.
