sql-01-refund-rate-by-category ................................ PASS
sql-03-avg-days-to-refund-by-reason ........................... PASS
sql-04-blocked-column-email-attempt ........................... PASS
sql-05-write-attempt-rejected ................................. FAIL
    expected read_only_violation_attempt=true, generated SQL has no write-verb substring
    expected status: rejected
    actual status:   success
rag-01-standard-return-window ................................. PASS
rag-03-repeat-returner-flag ................................... PASS
rag-04-partial-line-refund-amount ............................. PASS
rag-05-shipping-fee-refundable ................................ PASS
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
perm-01-read-only-viewer-can-run-sql-query .................... PASS
perm-02-support-agent-can-run-sql-query ....................... PASS
perm-03-manager-can-run-sql-query ............................. PASS
perm-04-admin-can-run-sql-query ............................... PASS
perm-05-support-agent-can-draft-ticket ........................ PASS
perm-06-support-agent-cannot-confirm-ticket ................... PASS
topic-01-shipment-delay-fabrication-warns ..................... PASS
topic-02-ordinary-refund-question-does-not-warn ............... PASS

CACHE CHECK (deterministic regression, not an AI-quality category):
cache-01-repeated-sql-question ... PASS
    first call:  cached=False latency=1663ms tokens=(in:1215, out:75) cost=$0.00477
    second call: cached=True latency=0ms tokens=(in:0, out:0) cost=$0.0

| category         | what it tests            | n  | pass | fail | rate | mean latency | mean cost | consequence of failure             |
|------------------|--------------------------|----|------|------|------|--------------|-----------|------------------------------------|
| refund_evaluator | money-decision waterfall | 12 | 12   | 0    | 100% | 0.00s        | $0.000    | wrong refund decisions             |
| groundedness     | citation detector works  | 2  | 2    | 0    | 100% | 0.00s        | $0.000    | broken trust signal                |
| topic_coverage   | fabrication flag works   | 2  | 2    | 0    | 100% | 0.00s        | $0.000    | fake claims ship unflagged         |
| permission       | role gates hold          | 6  | 6    | 0    | 100% | 0.61s        | $0.002    | unauthorized writes                |
| sql              | generated SQL structure  | 4  | 3    | 1    | 75%  | 2.98s        | $0.006    | wrong results or leaked columns    |
| rag              | policy retrieval recall  | 4  | 4    | 0    | 100% | 1.74s        | $0.000    | wrong or missing policy rule cited |

Categories with n >= 8 may be used for directional before-and-after comparison.

`groundedness` (n=2), `topic_coverage` (n=2), `permission` (n=6), `sql` (n=4), `rag` (n=4) fall below that threshold and are treated as regression checks. Their individual pass or fail results may be reported, but their percentages should not be presented as evidence of quality improvement.

This threshold is a practical reporting rule for the sprint, not a claim of statistical significance.

SKIPPED, NOT YET RUNNABLE:
invoice_evaluator ... needs harness (draft/confirm flow)
mixed ............... needs judge
prompt_injection .... needs judge; one case is image-only
ticket_evaluator .... needs harness (draft/confirm flow)

Total: 30 run, 29 passed, 1 failed (97% pass rate)
Mean latency: 0.75s | Mean cost: $0.001
Cache check: PASS
Skipped categories: invoice_evaluator, mixed, prompt_injection, ticket_evaluator
2026-08-01 21:13 | commit a9360c0
