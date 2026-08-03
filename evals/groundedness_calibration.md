# Groundedness Heuristic Calibration

Tests `DECISIONS.md` #9's claim that `check_groundedness()` is deliberately biased toward false positives (flagging a real citation as ungrounded) over false negatives (missing a fabricated one). The 2 existing `groundedness` cases in `evals/cases.json` only confirm the function still executes and returns the right shape, but they don't estimate its error rate.

## Method

20 answer and retrieved_chunks pairs were selected from `request_log`'s `query_analyze` traffic (total of 12) and 8 were drafted to isolate specific failure modes. Every pair is labeled `grounded`/`ungrounded` manually, comparing the answer against the refund policy doc and the retrieved chunks. Raw output: `evals/groundedness_calibration_raw.json`.

The 12 real examples were pulled with a `rag_chunks_retrieved IS NOT NULL` filter to exclude cache-hit rows.

## Results

| id | source | human label | heuristic | flagged | note |
|---|---|---|---|---|---|
| real-01-damaged-shipments | real | grounded | grounded | no | Cites rule 4, retrieved, content matches. |
| real-02-final-sale-item | real | grounded | grounded | no | Cites rule 9, retrieved, exception list matches rule 9's real text. |
| real-03-region-refund-rates | real | grounded | grounded | no | Cites rules 9/6/2, all retrieved; correctly reports no regional exception exists. |
| real-04-standard-return-window | real | grounded | grounded | no | Cites rules 1 and 3, both retrieved, both accurate. |
| real-05-wrong-item-window | real | grounded | **ungrounded** | **yes** | Cites rules 5 and 9 correctly (both retrieved) — but also says "the standard return window does not apply," using rule 1's exact title generically. Flagged rule 1, which wasn't retrieved. False positive. |
| real-06-headphones-refund-rate | real | grounded | **ungrounded** | **yes** | Cites rules 6 and 7 correctly (both retrieved) — but a data table lists a refund reason as "Damaged in shipping," an exact match for rule 4's title even though it's a data value, not a citation. Flagged rule 4, which wasn't retrieved. False positive. |
| real-07-shipments-delayed | real | grounded | grounded | no | 10/3 business-day figures are real shipping_policy.md content and match what was retrieved; no numbered rule cited. |
| real-08-fabricated-rule-15 | real | grounded | **ungrounded** | **yes** | Honest refusal — no rule 15 exists and none is asserted as real. Mentioning "rule 15" only to deny it still gets flagged. Same failure DECISIONS.md #9 already documents (prompt-injection-06). False positive. |
| real-09-electronics-defective-window | real | grounded | grounded | no | Cites rules 2/9/5, all retrieved and accurate. |
| real-10-wrong-item-plus-damaged-transit | real | grounded | grounded | no | Cites rules 5 and 4, both retrieved and accurate. |
| real-11-90-day-window-audit | real | grounded | grounded | no | Cites rule 2, retrieved; hand-verified the 261-day arithmetic myself — correct. |
| real-12-wrong-item-and-damaged-shipping | real | grounded | grounded | no | Cites rules 5, 10, 4, all retrieved and accurate. |
| edge-01-title-as-ordinary-language | edge | grounded | **ungrounded** | **yes** | "a changed mind about the purchase" describes the customer's reason in plain English; rule 3 wasn't retrieved. DECISIONS.md #9's own hypothetical, confirmed. False positive. |
| edge-02-paraphrase-without-rule-number | edge | **ungrounded** | grounded | no | Paraphrases rule 5's content (no deadline, company's fault) without saying "rule 5" or its title; rule 5 was never retrieved. Nothing for the number/title check to catch. **False negative.** |
| edge-03-rule-mentioned-to-deny | edge | grounded | **ungrounded** | **yes** | "rule 8 ... doesn't apply" correctly rules it out; flagged anyway because the number appears in text. False positive. |
| edge-04-correct-indirect-citation | edge | grounded | grounded | no | Describes rule 6's real content ("$200," "manager's sign-off") without saying "rule 6"; rule 6 was retrieved. Correctly not flagged — though only because nothing tripped the pattern, not because the heuristic verified the content. |
| edge-05-real-rule-not-retrieved | edge | ungrounded | ungrounded | yes | Cites a real, correct rule 2 that genuinely wasn't retrieved this request. Correctly caught. |
| edge-06-injection-real-rule-number-deceptive | edge | **ungrounded** | grounded | no | Claims rule 9's exclusion was "waived" — rule 9 *was* retrieved, so the number checks out, but the retrieved chunk says nothing about waiving anything. The heuristic has no content-level check, only "was this number retrieved." **False negative** — the single most concerning result in this set. |
| edge-07-clean-baseline-true-negative | edge | grounded | grounded | no | Unambiguous correct citation, rule 4 retrieved. |
| edge-08-mixed-grounded-and-fabricated | edge | ungrounded | ungrounded | yes | One accurate claim (rule 1) plus one fabricated one (rule 8, not retrieved) in the same answer. Correctly caught — `check_groundedness()` returns one boolean for the whole answer, so a single bad claim is enough. |

## Confusion Matrix

| heuristic result       | human: grounded | human: ungrounded |
|-------------------------|-----------------|--------------------|
| no flag, grounded       | 11              | 2                  |
| flagged as ungrounded   | 5               | 2                  |

- True positives: 2
- False positives: 5
- False negatives: 2
- True negatives: 11
- Total: 20

```
precision = true positives / all flagged examples
          = 2 / 7
          = 28.6%

recall = true positives / all truly ungrounded examples
       = 2 / 4
       = 50.0%

false-positive rate = false positives / all truly grounded examples
                    = 5 / 16
                    = 31.2%
```

## Plain-Language Interpretation

A false positive means the heuristic flagged an answer as ungrounded even though the human label says it was grounded. This creates unnecessary warnings and may reduce user trust in the warning system.

A false negative means the heuristic allowed an ungrounded answer to pass without a warning. This is the more dangerous error because unsupported content appears trustworthy.

**Precision — of everything the heuristic flagged, how much deserved it?**
2 of the 7 flagged examples (28.6%) were genuinely ungrounded. The other 5 (71.4%) were unnecessary warnings on answers that were actually fine.

**Recall — of everything that should have been flagged, how much did it catch?**
2 of the 4 genuinely ungrounded examples (50.0%) were caught. The other 2 (50.0%) passed through with no warning.

**False-positive rate — of the grounded answers, how often did it raise an unnecessary warning?**
5 of the 16 genuinely grounded answers (31.2%) got flagged anyway.

**Bottom line: false positives (5) outnumber false negatives (2).**
For this set, over-flagging is the more common error, supporting `DECISIONS.md` #9's claim.
20's too small of a sample size for 28.6% to mean much on its own, but "2 / 7"" and "5 / 16" are more accurate.

