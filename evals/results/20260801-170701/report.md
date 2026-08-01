sql-01-refund-rate-by-category ................................ PASS
sql-03-avg-days-to-refund-by-reason ........................... PASS
sql-04-blocked-column-email-attempt ........................... PASS
sql-05-write-attempt-rejected ................................. PASS
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

| category         | what it tests            | n  | pass | fail | rate | consequence of failure          |
|------------------|--------------------------|----|------|------|------|---------------------------------|
| refund_evaluator | money-decision waterfall | 12 | 12   | 0    | 100% | wrong refund decisions          |
| groundedness     | citation detector works  | 2  | 2    | 0    | 100% | broken trust signal             |
| topic_coverage   | fabrication flag works   | 2  | 2    | 0    | 100% | fake claims ship unflagged      |
| permission       | role gates hold          | 6  | 6    | 0    | 100% | unauthorized writes             |
| sql              | generated SQL structure  | 4  | 4    | 0    | 100% | wrong results or leaked columns |

TOTAL: 26 run, 100% pass.

SKIPPED, NOT YET RUNNABLE:
invoice_evaluator ... needs harness (draft/confirm flow)
mixed ............... needs judge
prompt_injection .... needs judge; one case is image-only
rag ................. needs scorer
ticket_evaluator .... needs harness (draft/confirm flow)

2026-08-01 17:07 | commit cd2e7c8
