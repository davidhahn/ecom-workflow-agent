refund-01-baseline-approval-damaged-shipping .................. PASS
refund-02-category-exclusion-final-sale ....................... PASS
refund-03-final-sale-exempt-reason-override ................... PASS
refund-04-time-window-violation-changed-mind .................. PASS
refund-05-time-window-violation-defective ..................... PASS
refund-06-evidence-missing-damaged-shipping ................... PASS
refund-08-could-not-process-ambiguous-reason .................. PASS
refund-09-could-not-process-unresolvable-product .............. PASS
ground-01-title-phrase-false-positive-rule-5 .................. PASS
ground-02-clean-grounded-citation ............................. PASS
refund-07-repeat-refund-flag-charlotte-dubois ................. PASS
refund-10-repeat-refund-flag-not-triggered-below-threshold .... PASS
refund-11-over-threshold-needs-manager ........................ PASS
refund-12-repeat-refund-flag-damaged-shipping-with-evidence ... PASS
topic-01-shipment-delay-fabrication-warns ..................... PASS
topic-02-ordinary-refund-question-does-not-warn ............... PASS
resilience-01-sql-tool-failure ................................ PASS
resilience-02-model-timeout ................................... PASS

CACHE CHECK (deterministic regression, not an AI-quality category):
cache-01-repeated-sql-question ... SKIPPED (deterministic subset, no live SQL call)

| category         | what it tests                                                 | n  | pass | fail | rate | mean latency | mean cost | consequence of failure                                                  |
|------------------|---------------------------------------------------------------|----|------|------|------|--------------|-----------|-------------------------------------------------------------------------|
| refund_evaluator | money-decision waterfall                                      | 12 | 12   | 0    | 100% | 0.01s        | $0.000    | wrong refund decisions                                                  |
| groundedness     | citation detector works                                       | 2  | 2    | 0    | 100% | 0.00s        | $0.000    | broken trust signal                                                     |
| topic_coverage   | fabrication flag works                                        | 2  | 2    | 0    | 100% | 0.00s        | $0.000    | fake claims ship unflagged                                              |
| resilience       | structured failure and retry behavior when a model call fails | 2  | 2    | 0    | 100% | 0.01s        | $0.000    | a hang, a blank success, or a made-up answer instead of an honest error |

Categories with n >= 8 may be used for directional before-and-after comparison.

`groundedness` (n=2), `topic_coverage` (n=2), `resilience` (n=2) fall below that threshold and are treated as regression checks. Their individual pass or fail results may be reported, but their percentages should not be presented as evidence of quality improvement.

This threshold is a practical reporting rule for the sprint, not a claim of statistical significance.

SKIPPED, NOT YET RUNNABLE:
invoice_evaluator ........................................... needs harness (draft/confirm flow)
mixed ....................................................... not yet runnable
permission .................................................. not yet runnable
prompt_injection ............................................ not yet runnable
rag ......................................................... not yet runnable
request_faithfulness ........................................ not yet runnable
sql ......................................................... not yet runnable
sql_semantic ................................................ not yet runnable
ticket_evaluator ............................................ needs harness (draft/confirm flow)
prompt-injection-03-ticket-fabricated-category .............. needs ticket draft/confirm harness
prompt-injection-04-ticket-fabricated-customer-resolution ... needs ticket draft/confirm harness
prompt-injection-07-invoice-arithmetic-bypass ............... image-only case, no text harness

Total: 18 run, 18 passed, 0 failed (100% pass rate)
Mean latency: 0.01s | Mean cost: $0.000
Cache check: SKIPPED
Skipped categories: invoice_evaluator, mixed, permission, prompt_injection, rag, request_faithfulness, sql, sql_semantic, ticket_evaluator
2026-09-01 18:59 | commit 0706b2f
