# Evals

A quick overview of four of the categories in `evals/cases.json`. Each section explains the following:
- What each one is actually checking
- Why it can be scored with a plain equality check instead of a judgment call
- What it means when one fails

## `refund_evaluator`

This is the category that deals with financial data, so it also has the most cases: 12. Each case feeds a resolved refund request and real order data into `evaluate_refund()` and checks two things: did it land on the right outcome, and did it point to the actual policy rule that made the call. `evaluate_refund()` is a pure function with no LLM involvement in the decision, so the expected value in each case can be traced exactly against the data that actually exists in the database. When one of these fails, it means the system is telling a customer wrong information.

## `groundedness`

Two cases test whether `check_groundedness()` itself still works, not whether the app's answers are generally grounded. The function flags when an answer cites a policy rule that was never actually retrieved, and these cases confirm that detection still fires correctly. Scoring is exact because both cases feed a fixed answer and a fixed set of retrieved chunks directly into the function. When this fails, a hallucinated rule can drive a real refund decision.

## `topic_coverage`

This is a second, independent guard checking a different failure mode. It checks whether an answer makes shipment or delivery claims when the tool loop never queried shipment data at all. Like groundedness, it's a deterministic keyword check on a fixed answer and a record of what was actually queried, so scoring is unambiguous. When this fails, the system can state something about a shipment with nothing backing it up.

## `permission`

These six cases are more of an integration test than a model eval. They confirm a given role either gets to call an endpoint or gets a 403, matching what's declared in the tool registry. A support agent being able to draft a ticket but not confirm one is one example. Scoring is exact because it's just checking a status code against a role/tool pair defined in code. A miss here isn't a quality regression, it's an access-control hole.

## Why these four first

None of these four categories actually measure LLM quality. They should score at or near 100%, and that's by design. They're the control group: no model calls, no cost, no variance, and outcomes that are already known. They prove the harness, case data, and reporting work before any of this gets pointed at real, noisy model behavior. They'll later anchor a deterministic CI gate. A failure here means a bug in the implementation, the harness, or the fixture data, not the model.
