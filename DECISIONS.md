# Engineering decisions

I kept this log to record choices that shaped the project, including the evidence behind them and the costs I accepted.

[Architecture](ARCHITECTURE.md) describes the current system. This log preserves how it developed; later entries sometimes update earlier decisions. Dates are carried over from the previous index, and decision numbers stay fixed even where date order differs.

The [full earlier record](https://github.com/davidhahn/ecom-workflow-agent/blob/9562c8114d1a9e77e5db4737f2f3d9083542d4f6/DECISIONS.md) preserves longer investigation notes, migration identifiers, and test details omitted from this shorter edition.

## Start here

- [6. Restrict access to customer columns](#decision-6): A database grant behaved differently from what I expected.
- [33. Check SQL results against known answers](#decision-33): Structural checks missed incorrect calculations.
- [44. Keep Sonnet for the current workflows](#decision-44): Model comparisons exposed differences in financial and policy answers.
- [45. Defer the investigation pipeline](#decision-45): Existing failures took priority over another answer-producing workflow.
- [52–53. Calibrate production retrieval](#decision-52): Changing providers exposed a ranking problem.

## Browse by topic

### Data and API contracts

- [1. Generate frontend types from the API schema](#decision-1)
- [2. Run only the database in Docker Compose](#decision-2)
- [3. Manage schema changes with SQLAlchemy and Alembic](#decision-3)
- [4. Seed reproducible business scenarios](#decision-4)
- [13. Store absent retrieval data as SQL NULL](#decision-13)
- [14. Keep time-sensitive fixtures reachable](#decision-14)
- [15. Convert JSON fixtures to typed grounding inputs](#decision-15)
- [19. Register all database models in test setup](#decision-19)
- [25. Seed a traceable revenue-drop scenario](#decision-25)

### SQL access and execution

- [5. Validate SQL and restrict database access](#decision-5)
- [6. Grant access to explicit customer columns](#decision-6)
- [29. Give refund evaluation its own database role](#decision-29)

### Refunds and permissions

- [10. Apply refund rules in a fixed order](#decision-10)
- [11. Resolve extracted refund details against orders](#decision-11)
- [12. Deny refund requests with missing evidence](#decision-12)
- [16. Require a customer identifier for refund resolution](#decision-16)
- [20. Read tool permissions from the registry](#decision-20)
- [21. Reject duplicate invoices before insertion](#decision-21)
- [51. Extract product names without quantity](#decision-51)

### Retrieval and answer checks

- [7. Split policy documents at rule boundaries](#decision-7)
- [8. Use local embeddings during development](#decision-8)
- [9. Check named policy citations as well as numbers](#decision-9)
- [17. Return an explicit incomplete state at the loop limit](#decision-17)
- [18. Make grounding warnings visible](#decision-18)
- [27. Ingest policy passages during deployment](#decision-27)
- [32. Keep citation matching scoped to source checks](#decision-32)
- [39. Calibrate a local retrieval threshold](#decision-39)
- [52. Calibrate retrieval for the production provider](#decision-52)
- [53. Keep the production ranking failure visible](#decision-53)

### Evaluations and model choices

- [26. Build the investigation evidence stages first](#decision-26)
- [28. Prioritize evaluations before more features](#decision-28)
- [30. Bypass cache and rate limits during evaluations](#decision-30)
- [31. Record the limits of bulk refusal cases](#decision-31)
- [33. Check SQL results against known answers](#decision-33)
- [34. Test plausible SQL calculation errors](#decision-34)
- [35. Report why a SQL result failed](#decision-35)
- [36. Measure SQL correctness across repeated runs](#decision-36)
- [37. Clarify refund-rate calculations in the SQL prompt](#decision-37)
- [40. Distinguish measured fixes from preventive work](#decision-40)
- [41. Keep the judge fixed during model comparisons](#decision-41)
- [43. Compare experiments on a frozen harness](#decision-43)
- [44. Keep Sonnet for the current workflows](#decision-44)
- [45. Defer the investigation pipeline](#decision-45)
- [46. State the write boundary in the analyze prompt](#decision-46)
- [47. Run a deterministic evaluation subset in CI](#decision-47)
- [48. Record live model calls remaining in pytest](#decision-48)
- [49. Verify both CI checks with an injected regression](#decision-49)
- [50. Exercise the deployed request paths](#decision-50)

### Deployment and request tracing

- [22. Distinguish absent traces from zero tool calls](#decision-22)
- [23. Check the proxy secret in the backend](#decision-23)
- [38. Retry covered model calls once](#decision-38)
- [54. Return request IDs for direct trace links](#decision-54)
- [55. Link cached answers to their original trace](#decision-55)
- [56. Measure model-call time directly](#decision-56)

### Frontend

- [24. Test frontend interactions with Vitest](#decision-24)
- [57. Keep proxy middleware under src](#decision-57)
- [58. Give the project a homepage before the scenarios](#decision-58)
- [59. Show captured results before a live run](#decision-59)
- [60. Use established UI components](#decision-60)

## Decision record

<a id="1-packagesshared-generated-only-nothing-hand-written"></a>
<a id="decision-1"></a>

### 1. Generate frontend types from the API schema

*2026-07-06*

I chose to generate shared TypeScript types from FastAPI's OpenAPI schema. This gives the frontend and backend one contract to work from.

Backend schema changes require rerunning code generation. Until that happens, generated types can be stale.

**Evidence:** [Generated types](packages/shared/README.md).


<a id="2-docker-compose-scope-database-only-no-app-services-yet"></a>
<a id="decision-2"></a>

### 2. Run only the database in Docker Compose

*2026-07-06*

I kept Compose limited to Postgres and pgvector while verifying the application paths separately.

Local development requires starting the API and frontend separately. The original choice reflected the project's Part 1 scope.

<a id="3-sqlalchemy--alembic-vs-raw-sql-migrations"></a>
<a id="decision-3"></a>

### 3. Manage schema changes with SQLAlchemy and Alembic

*2026-07-06*

I chose SQLAlchemy models and Alembic migrations so schema changes have a reviewable history.

Autogenerated migrations still need manual review, including constraint names and index changes, before they are applied.

<a id="4-seed-strategy-deterministic-truncate-and-reinsert-vs-randomizedfaker-generated-per-run"></a>
<a id="decision-4"></a>

### 4. Seed reproducible business scenarios

*2026-07-06*

I used a fixed set of fixtures and a truncate-and-reinsert script so specific refund cases could be found after each reset.

The small dataset offers limited realism, and reseeding replaces demo records. Time-sensitive fixtures needed the later adjustment in [14](#decision-14).

<a id="5-sql-query-path-four-independent-differently-shaped-safety-layers"></a>
<a id="decision-5"></a>

### 5. Validate SQL and restrict database access

*2026-07-07*

**Decision:** I combined SQL validation, an estimated-cost limit, and a restricted database role. Audit logs record attempts and their outcomes.

**Why:** These controls address different risks. Validation rejects prohibited statements; cost checks limit expensive queries; database grants restrict access even when validation misses an operation. Logging supports inspection after the attempt.

**Tradeoff:** Each request adds parsing, an EXPLAIN round trip, and logging. None of these controls establishes that an allowed query calculates the correct answer; [33](#decision-33) added that evaluation.

**Evidence:** [SQL service](apps/api/app/query/service.py).


<a id="6-layer-3-column-restriction-allowlist-grant-not-table-grant-then-revoke"></a>
<a id="decision-6"></a>

### 6. Grant access to explicit customer columns

*2026-07-07*

**Decision:** I granted the SQL role access to an explicit list of customer columns, excluding email.

**Why:** My first migration granted table-wide access, then revoked access to email. A direct query under the restricted role still returned email because the table grant remained in effect.

**Tradeoff:** New customer columns require a deliberate grant update. After the fix, selecting email failed with permission denied while allowed reads still succeeded.

**Evidence:** [SQL role migration](apps/api/alembic/versions/e226476acfd7_create_ops_agent_readonly_role_with_.py).


<a id="7-rag-chunking-structural-per-h2--per-rule-not-fixed-size-or-semantic"></a>
<a id="decision-7"></a>

### 7. Split policy documents at rule boundaries

*2026-07-08*

**Decision:** I used H2 sections as chunk boundaries and preserved the source document and rule number as metadata.

**Why:** The authored policies already gave each rule its own section. Keeping that structure avoids splitting a rule across arbitrary text windows.

**Tradeoff:** This assumes the documents follow the expected heading structure. Mixed formats or several rules under one heading would need a different ingestion strategy.

<a id="8-local-baaibge-m3-embeddings-over-a-hosted-embedding-api"></a>
<a id="decision-8"></a>

### 8. Use local embeddings during development

*2026-07-08*

**Decision:** I initially chose BAAI/bge-m3 for a small corpus to avoid a hosted embedding dependency and per-call charges.

**Why:** The model's download and memory footprint later exceeded the deployment environment. Production switched to Voyage through `EMBEDDING_PROVIDER`, with 1024-dimensional output matching the existing vector column.

**Tradeoff:** Local development retained BAAI/bge-m3. Provider changes also change retrieval behavior; [52](#decision-52) and [53](#decision-53) record the production calibration and remaining gap.

<a id="9-groundedness-check-catches-named-citations-not-just-numeric-ones"></a>
<a id="decision-9"></a>

### 9. Check named policy citations as well as numbers

*2026-07-09*

**Decision:** I extended grounding checks to recognize policy titles using a map built from the ingestion chunker.

**Why:** An answer mentioned “Wrong Item Shipped” even though rule 5 had not been retrieved. Numeric-only matching would have missed the citation.

**Tradeoff:** Literal matching can flag a title used as ordinary language or a rule mentioned in a refusal. It can also miss paraphrases. [32](#decision-32) records calibration examples; the check does not establish meaning.

**Evidence:** [Citation checker](apps/api/app/orchestrator/groundedness.py).


<a id="10-refund-evaluator-sequential-first-match-wins-not-repeat-flag-overrides-everything"></a>
<a id="decision-10"></a>

### 10. Apply refund rules in a fixed order

*2026-07-09*

**Decision:** I ordered the evaluator's rules by category exclusion, time window, evidence, repeat-refund flag, and approval threshold. The first decisive rule wins.

**Why:** I interpreted rule 7's “regardless of reason or amount” as applying after validity checks. A final-sale exclusion therefore denies a request before the customer-level repeat flag is considered.

**Tradeoff:** The original wording left room for interpretation. If the policy owner intends the repeat flag to override all outcomes, this ordering needs revision.

**Evidence:** [Refund evaluator](apps/api/app/orchestrator/refund_evaluator.py).


<a id="11-refundevaluate-extraction-resolves-order_item_id-via-db-lookup-not-an-llm-guess"></a>
<a id="decision-11"></a>

### 11. Resolve extracted refund details against orders

*2026-07-09*

**Decision:** Claude extracts customer and product identifiers, reason, and confidence. Code resolves an `order_item_id` through a database lookup.

**Why:** The model should not invent record IDs. Unresolved products or uncertain reasons returned `could_not_process` in the seeded checks.

**Tradeoff:** The lookup selected the most recent matching order item. Requests with several plausible matches need stronger disambiguation. [16](#decision-16) later removed the product-only fallback when no customer was named.

<a id="12-evidence-check-outcome-corrected-from-pending-to-denied"></a>
<a id="decision-12"></a>

### 12. Deny refund requests with missing evidence

*2026-07-09*

**Decision:** I changed the evaluator's missing-evidence outcome from `pending` to `denied`.

**Why:** The evaluator had no persisted waiting state, evidence-upload endpoint, or follow-up flow. Returning pending implied work the system could not resume.

**Tradeoff:** Stored refund rows can still use pending for other workflows. The affected fixture was updated separately, and the with-evidence scenario continued to approve.

<a id="13-rag_chunks_retrieved-needed-jsonbnone_as_nulltrue-not-the-plain-type"></a>
<a id="decision-13"></a>

### 13. Store absent retrieval data as SQL NULL

*2026-07-10*

I set `JSONB(none_as_null=True)` for nullable retrieval data. A raw database check had shown that Python `None` was stored as JSON null, which still satisfied `IS NOT NULL`.

After the change, SQL and refund requests stored SQL NULL while retrieval paths stored chunk arrays. Future nullable JSON columns need the same explicit choice.

<a id="14-seed-data-uses-fixed-historical-dates-not-time-relative-offsets"></a>
<a id="decision-14"></a>

### 14. Keep time-sensitive fixtures reachable

*2026-07-13*

**Decision:** The original fixture strategy used fixed historical dates. As time passed, refund-window and repeat-refund cases stopped exercising their intended branches.

**Why:** I changed the affected rules 2, 3, and 7 fixtures to offsets from a shared `NOW`, while leaving the bulk historical data anchored. Database checks across two reseeds confirmed those branches remained reachable.

**Tradeoff:** Time-sensitive records now vary by seed date. The approval-threshold fixture was still a separate gap at this stage; later CI verification in [49](#decision-49) exercised that outcome.

<a id="15-groundedness-eval-cases-reconciling-json-fixtures-with-typed-function-input"></a>
<a id="decision-15"></a>

### 15. Convert JSON fixtures to typed grounding inputs

*2026-07-14*

**Decision:** I added `chunk_from_dict()` beside `RagChunkResult` so stored JSON fixtures could supply the objects expected by `check_groundedness()`.

**Why:** Executing a fixture exposed an attribute-access error that schema validation alone missed. The checker expected `chunk.rule_number`, while JSON supplied dictionaries.

**Tradeoff:** The function kept its typed contract. Future fixtures for typed inputs need an explicit conversion too, rather than ad hoc dict/object fallbacks.

**Evidence:** [Typed chunks](apps/api/app/rag/schemas.py).


<a id="16-refund-resolution-requires-a-customer-identifier-or-it-refuses-outright"></a>
<a id="decision-16"></a>

### 16. Require a customer identifier for refund resolution

*2026-07-14*

**Decision:** I removed the product-only fallback from `resolve_order_item()`. Missing customer details now return `could_not_process`.

**Why:** The fallback searched across customers and could evaluate someone else's order. The architecture critique exposed that risk; a request naming a real customer still resolved after the fix.

**Tradeoff:** The system refuses underspecified requests even when a product happens to be unique. A clarification workflow remains unimplemented.

**Evidence:** [Original critique](ARCHITECTURE_CRITIQUE.md).


<a id="17-tool-loop-exhaustion-returns-an-explicit-incomplete-state-not-a-silently-empty-answer"></a>
<a id="decision-17"></a>

### 17. Return an explicit incomplete state at the loop limit

*2026-07-14*

**Decision:** I added `AnalyzeResponse.incomplete` when Claude exhausted the allowed tool rounds.

**Why:** The old path returned an empty answer that passed grounding checks. The new branch skips that check and explains that the request did not complete.

**Tradeoff:** Clients must inspect the new field. The response explains the outcome, while diagnosing the unfinished work still requires the request log.

**Evidence:** [Analyze service](apps/api/app/orchestrator/analyze_service.py).


<a id="18-groundedness-warning-made-visually-prominent-not-gating"></a>
<a id="decision-18"></a>

### 18. Make grounding warnings visible

*2026-07-14*

**Decision:** I placed a prominent warning and the flagged claims above answers whose grounding check failed.

**Why:** The previous small badge was easy to overlook beside a full answer.

**Tradeoff:** The answer remains visible because no regeneration or escalation flow was added. Users can still act on it, and the heuristic's false positives remain. See [32](#decision-32).

<a id="19-test-isolation-requires-explicitly-importing-every-model-module-not-just-the-one-under-test"></a>
<a id="decision-19"></a>

### 19. Register all database models in test setup

*2026-07-18*

**Decision:** I added explicit imports for the model modules in `tests/__init__.py`, following Alembic's existing setup.

**Why:** A ticket test passed in the full suite but failed alone because SQLAlchemy had not registered the table referenced by a request-log foreign key.

**Tradeoff:** New model modules need to join that import list. Isolated test runs help expose missing registration that a full suite can conceal.

<a id="20-permission-enforcement-v1-one-dependency-keyed-by-tool_name-against-the-registry-not-by-endpoint"></a>
<a id="decision-20"></a>

### 20. Read tool permissions from the registry

*2026-07-18*

**Decision:** I used one `require_permission(tool_name, request_type)` dependency to check the registry's required permission against the demo role.

**Why:** Drafting and confirming need different access even within one workflow. Missing or invalid roles fall back to `read_only_viewer`, and denials are logged.

**Tradeoff:** The role comes from a caller-set header, so it does not verify identity. Analyze and refund evaluation were left outside this dependency because their paths were read-only.

**Evidence:** [Permission checks](apps/api/app/permissions.py).


<a id="21-vendor-invoice-draftconfirm-a-confirm-time-duplicate-refuses-the-write-it-doesnt-insert-a-duplicate-row"></a>
<a id="decision-21"></a>

### 21. Reject duplicate invoices before insertion

*2026-07-19*

**Decision:** I rechecked invoice duplicates at confirmation and returned a structured error before inserting a duplicate vendor/invoice-number pair.

**Why:** The database's unique index made a persisted duplicate row incompatible with the proposed duplicate status. Confirmation reuses the draft store, expiry, and permission checks.

**Tradeoff:** Arithmetic and date checks were not rerun because draft fields could not change. A follow-up expanded logs for success, idempotent retries, and duplicate rejection; a database assertion verified the full invoice details were recorded.

**Evidence:** [Invoice tests](apps/api/tests/test_invoices.py).


<a id="22-tool-call-tracing-tool_calls-is-null-for-every-request-type-except-analyze-and-never-null-for-that-one"></a>
<a id="decision-22"></a>

### 22. Distinguish absent traces from zero tool calls

*2026-07-19*

**Decision:** I stored `tool_calls` as a list for analyze requests and NULL for other request types.

**Why:** An empty list means the analyze path ran without tools. NULL means that request type has no tool-call trace. The detail endpoint includes the trace; the list response omits it.

**Tradeoff:** Sequence numbers follow dispatch order. Tool timing excludes model processing, so the original derived remainder was imprecise. [56](#decision-56) added measured model-call time.

<a id="23-deployed-perimeter-shared-secret-header-rendervercel-plus-cors-as-an-independent-second-layer-not-one-mechanism-doing-both-jobs"></a>
<a id="decision-23"></a>

### 23. Check the proxy secret in the backend

*2026-07-22*

**Decision:** I added a backend secret check for requests other than health, alongside a browser-origin allowlist. The frontend proxy injects the secret server-side.

**Why:** The backend needs to enforce the header itself. CORS separately controls browser origins and does not authenticate server-to-server calls.

**Tradeoff:** The secret must match in two hosting environments. CORS was also reordered to run outside the secret check, so browser preflights could reach the allowlist. Tests verified allowed-origin 200 and rejected-origin 400 responses.

**Evidence:** [CORS tests](apps/api/tests/test_cors.py).


<a id="24-frontend-test-framework-vitest--react-testing-library-added-when-the-first-real-test-was-needed"></a>
<a id="decision-24"></a>

### 24. Test frontend interactions with Vitest

*2026-07-23*

**Decision:** I added Vitest and React Testing Library when example chips and the shared banner needed interaction tests.

**Why:** Those checks exercised component behavior, such as filling a field without submitting it. They did not require a full browser and two running services.

**Tradeoff:** Cleanup is wired explicitly. The banner tests reproduce layout composition without executing the real layout, so layout integration still needs verification. The development proxy issue mentioned during this work was later fixed in [57](#decision-57).

<a id="25-web_analyticscampaigns-schema--revenue-drop-seed-story-part-3-demo-query-why-did-revenue-drop-last-week"></a>
<a id="decision-25"></a>

### 25. Seed a traceable revenue-drop scenario

*2026-07-24*

**Decision:** I added campaign and web-analytics data while calculating revenue from orders, avoiding a second stored revenue total.

**Why:** The fixtures linked a campaign ending to about 26% fewer sessions and a 28% revenue drop, with 44% fewer orders and flat refunds. A campaign note supplied context beyond the rows.

**Tradeoff:** Existing fixtures initially reversed the intended trend. I corrected the new rows against combined database totals and used a shared seed-time timestamp to keep the scenario recent.

<a id="26-investigation-pipeline-planner--data-analyst-only-reuse-run_sql_queryquery_rag-as-is-per-signal-error-isolation-no-report-writer-yet"></a>
<a id="decision-26"></a>

### 26. Build the investigation evidence stages first

*2026-07-25*

**Decision:** I implemented a Planner and Data Analyst, exposing `investigate_gather_evidence()` for direct testing. The Planner proposes signals; the analyst reuses SQL and retrieval services.

**Why:** Per-signal handling lets other evidence complete when one call fails. A test injected one failure among four signals and checked that the other three succeeded.

**Tradeoff:** The work also required analytics tables in the SQL allowlist and database grants. No endpoint or final answer stage was added. [45](#decision-45) records what completing the pipeline would require.

**Evidence:** [Evidence gathering](apps/api/app/orchestrator/data_analyst.py).


<a id="27-rag-ingestion-added-to-renderyamls-predeploycommand-not-left-as-a-manual-step"></a>
<a id="decision-27"></a>

### 27. Ingest policy passages during deployment

*2026-07-29*

**Decision:** I added policy ingestion after migrations in the pre-deploy command.

**Why:** The deployed app returned empty policy results because migrations created `policy_chunks` without populating it. The business-data reseed job did not ingest documents.

**Tradeoff:** An embedding-provider failure can now block deployment. Business fixtures remain on a separate daily reset; policy passages are regenerated during deploys.

**Evidence:** [Deployment configuration](render.yaml).


<a id="28-next-15-days-eval-depth-over-feature-breadth"></a>
<a id="decision-28"></a>

### 28. Prioritize evaluations before more features

*2026-07-30*

**Decision:** I set aside the next development period for model configuration, repeated evaluations, judge review, and a model comparison.

**Why:** I wanted evidence about where the cheaper model worked and where it failed. Existing gaps needed inspection before adding another answer-producing workflow.

**Tradeoff:** The Report Writer, reranker, real authentication, ticket/invoice UI, and partial-quantity refunds were deferred. These were portfolio scope choices, not claims of customer readiness. Later retrieval findings in [52–53](#decision-52) changed the evidence behind further search work.

<a id="29-refund-evaluator-its-own-restricted-db-role"></a>
<a id="decision-29"></a>

### 29. Give refund evaluation its own database role

*2026-08-06*

**Decision:** I replaced the evaluator's full-access database connection with `refund_evaluator_readonly`, limited to the five tables it needed.

**Why:** The evaluator reads records and returns a decision without writing a refund. A test checks that it uses the restricted role.

**Tradeoff:** This role can read email to resolve a customer, while the generated-SQL role excludes it. Email stays out of the evaluator response, but the two permission sets need separate maintenance.

<a id="30-new-eval-category-request_faithfulness-needed-two-app-changes-not-just-test-cases"></a>
<a id="decision-30"></a>

### 30. Bypass cache and rate limits during evaluations

*2026-08-07*

**Decision:** I added request-level cache bypass and an `EVAL_RATE_LIMIT_BYPASS` setting for repeated evaluation calls.

**Why:** Cached answers could hide model variance, and the analyze endpoint's rate limit prevented the planned repeated runs.

**Tradeoff:** Rate-limit bypass applies to the whole evaluation process because the limiter runs before request-body parsing. It must remain an evaluation environment setting.

<a id="31-request_faithfulnesss-first-6-cases-are-all-bulkabstract-requests-not-mixed-08s-shape"></a>
<a id="decision-31"></a>

### 31. Record the limits of bulk refusal cases

*2026-08-07*

**Decision:** I kept the six request-faithfulness cases while documenting what their 18 passing calls established.

**Why:** All responses refused before using tools. The original `mixed-08` failure involved a specific resolved refund whose status could substitute for the requested action.

**Tradeoff:** Bulk refusals did not reproduce that situation. The original case needed direct follow-up, which arrived in [46](#decision-46).

**Evidence:** [Refusal calibration](evals/request_faithfulness_calibration.md).


<a id="32-groundedness-heuristic-four-ways-it-gets-fooled"></a>
<a id="decision-32"></a>

### 32. Keep citation matching scoped to source checks

*2026-08-07*

**Decision:** I retained the structural checker while recording its calibration failures. It matches rule text and identifiers, without reading the meaning of a claim.

**Why:** The 20 examples included a waived-rule claim that passed, correct denials that were flagged, uncited text outside its matching scope, and titles used as ordinary words. Five examples were over-flagged and two problems were missed.

**Tradeoff:** The sample is small, and some patterns existed only in calibration records. A matching citation cannot establish that a rule was applied correctly. The answer warning should be interpreted with that limit.

**Evidence:** [Labeled calibration examples](evals/groundedness_calibration_raw.json).


<a id="33-sql-eval-cases-now-check-the-actual-number-not-just-the-query-shape"></a>
<a id="decision-33"></a>

### 33. Check SQL results against known answers

*2026-08-08*

**Decision:** I added independently calculated expected values to the three SQL cases.

**Why:** The Electronics refund-rate query returned 50% by counting order lines. Refunded units divided by units sold gave 43.48%. The new check exposed the error, which I left failing for the application fix.

**Tradeoff:** Comparisons inspect returned rows, so they do not verify how the final answer states the result. Rejected operations still need status assertions. [37](#decision-37) records the generation fix.

**Evidence:** [SQL calibration](evals/sql_semantic_calibration.md).


<a id="34-new-sql_semantic-category-four-traps-that-make-a-wrong-query-look-right"></a>
<a id="decision-34"></a>

### 34. Test plausible SQL calculation errors

*2026-08-08*

**Decision:** I added four semantic cases covering denominator choice, duplicated joins, status filtering, and customer filtering.

**Why:** The Home refund-rate case exposed another units-versus-rows error and inclusion of non-approved refunds. These queries could pass structural checks.

**Tradeoff:** The cases also exposed rejection of valid `COUNT(*)` queries. That validator defect remained open during measurement and was fixed in [37](#decision-37).

**Evidence:** [Semantic cases](evals/cases.json).


<a id="35-sql-result-failures-get-a-specific-reason-not-one-generic-message"></a>
<a id="decision-35"></a>

### 35. Report why a SQL result failed

*2026-08-08*

**Decision:** I expanded failure records to distinguish rejected queries, missing rows, nonnumeric values, and incorrect results. Records retain generated SQL and returned rows.

**Why:** The previous generic mismatch message made diagnosis harder. Rerunning the two known failures confirmed that the new messages exposed their results.

**Tradeoff:** Root cause still requires inspecting SQL. A displayed scalar can select an unrelated numeric field, so the full saved rows remain important. Hand-written review notes supplement the report where available.

**Evidence:** [Evaluation runner](evals/run.py).


<a id="36-sql-semantic-accuracy-measured-for-real-4-of-7-cases-wrong-3-times-in-a-row"></a>
<a id="decision-36"></a>

### 36. Measure SQL correctness across repeated runs

*2026-08-09*

**Decision:** I ran seven SQL cases three times with cache bypass and kept semantic results separate from structural safety.

**Why:** Two cases calculated the same wrong rates repeatedly. A separate valid `COUNT(*)` query was rejected once and passed twice, exposing a validator problem alongside the calculation errors.

**Tradeoff:** I recorded the failures before changing application behavior. The before/after comparison in [37](#decision-37) uses 14/21 correct outcomes as its baseline; this entry's earlier title overstated the number of consistently failing cases.

**Evidence:** [Baseline calibration](evals/sql_semantic_calibration_v1.md).


<a id="37-prompt-v2-one-targeted-addition-fixed-both-confirmed-sql-bugs-first-try"></a>
<a id="decision-37"></a>

### 37. Clarify refund-rate calculations in the SQL prompt

*2026-08-10*

**Decision:** I added a calculation explanation and worked example covering unit quantities and approved refunds, then versioned the SQL prompt through responses and query audit records.

**Why:** Seven cases over three runs improved from 14/21 correct outcomes to 21/21. The new SQL used `COUNT(*)` more often, exposing an existing validator defect that I also fixed.

**Tradeoff:** Measured latency rose from 2.83s to 3.26s and cost from $0.0060 to $0.0068 per call. The small repeated set supports the observed improvement, with limited evidence about unseen questions.

**Evidence:** [Before/after results](evals/primary_results.md).


<a id="38-one-bounded-retry-for-anthropic-calls-on-the-sql-and-analyze-paths-only"></a>
<a id="decision-38"></a>

### 38. Retry covered model calls once

*2026-08-11*

**Decision:** I added a 30-second timeout and one retry after a two-second delay for transient errors in SQL generation and analyze calls. SDK retries were disabled to avoid stacking policies.

**Why:** Mocked failures verified structured error or incomplete responses after both attempts failed, with `retry_count` recorded in request logs.

**Tradeoff:** This was preventive work, scoped to those paths. Other model-call sites were outside the wrapper at the time. The fixed delay was chosen for a single retry.

**Evidence:** [Retry tests](apps/api/tests/test_llm_retry.py).


<a id="39-retrieval-threshold-picking-046-from-labeled-calibration-data"></a>
<a id="decision-39"></a>

### 39. Calibrate a local retrieval threshold

*2026-08-12*

**Decision:** I chose a distance cutoff of 0.46 from 54 hand-labeled candidates across 18 questions.

**Why:** It retained every clearly relevant example in the sample. Relevant and irrelevant distances overlapped, so no cutoff separated them cleanly.

**Tradeoff:** An off-topic case still passed through. The sample had one labeler and limited questions. [52](#decision-52) later established a separate production-provider threshold.

**Evidence:** [Retrieval calibration](evals/rag_retrieval_calibration.md).


<a id="40-what-justified-the-sql-fix-the-threshold-and-the-retry-work-without-an-incident-behind-any-of-them"></a>
<a id="decision-40"></a>

### 40. Distinguish measured fixes from preventive work

*2026-08-12*

**Decision:** I recorded why the SQL, retrieval, and retry changes had different kinds of support.

**Why:** The SQL change followed repeated calculation failures. Retrieval used labeled calibration. Retry behavior was tested with injected failures before any production incident motivated it.

**Tradeoff:** Passing trials did not establish broad reliability. The individual limits remain with [37](#decision-37), [38](#decision-38), and [39](#decision-39), rather than treating all three as equivalent evidence.

<a id="41-a-model-comparison-would-have-quietly-graded-itself"></a>
<a id="decision-41"></a>

### 41. Keep the judge fixed during model comparisons

*2026-08-13*

**Decision:** I separated `JUDGE_MODEL` from the application model setting and added `--model`, automatic cache bypass, and experiment metadata to the runner.

**Why:** Changing the application model had also changed the judge. The new metadata records both models, prompt versions, dataset hash, commit, and cache setting. A 62-case run verified the recording path.

**Tradeoff:** Live request logs still lacked model versions. The dataset hash changes even for textual edits. The comparison itself followed in [44](#decision-44).

**Evidence:** [Evaluation runner](evals/run.py).


<a id="42-number-skipped-no-entry-was-ever-recorded-under-it"></a>
<a id="decision-42"></a>

### 42. Unused number

No decision was recorded under this number. It is reserved to preserve existing references.

<a id="43-rebuilt-the-ablation-table-on-a-frozen-harness-and-found-a-second-cache-bug-doing-it"></a>
<a id="decision-43"></a>

### 43. Compare experiments on a frozen harness

*2026-08-14*

**Decision:** I rebuilt the ablation table with one 27-case set, repeated three times per configuration. Earlier rows used changing case sets and measurement methods.

**Why:** The first run exposed cached baseline retrieval reused across variants. Adding RAG cache bypass and rerunning affected cases produced SQL 14/21 → 21/21, off-topic refusal 0/15 → 12/15, and resilience 0/6 → 6/6. On-topic retrieval stayed 36/36.

**Tradeoff:** Scorer changes remained outside this application comparison. Reconstructing older configurations tests them under the frozen harness, rather than reproducing every detail of their original environment.

**Evidence:** [Ablation report](evals/ablation_table.md).


<a id="44-staying-on-sonnet-and-turning-down-a-workload-split"></a>
<a id="decision-44"></a>

### 44. Keep Sonnet for the current workflows

*2026-08-17*

**Decision:** I kept Sonnet and deferred routing selected requests to Haiku.

**Why:** In the compared SQL and mixed categories, nine paired outcomes passed on Sonnet and failed on Haiku; three went the other way, all on `mixed-08`. Inspected failures involved tool use, retrieval wording, date math, and currency conversion.

**Tradeoff:** Haiku offered roughly threefold cost savings and lower latency in those categories. Routing needed a classifier with little evaluation coverage. Some inspected traces came from later reruns. [46](#decision-46) subsequently fixed Sonnet's write-refusal case.

**Evidence:** [Model comparison and recommendation](evals/model_recommendation.md).


<a id="45-closing-the-investigation-pipeline-as-a-formal-scope-deferral"></a>
<a id="decision-45"></a>

### 45. Defer the investigation pipeline

*2026-08-16*

**Decision:** I left the Planner and Data Analyst available for direct tests and deferred the Report Writer, endpoint, and UI.

**Why:** Existing measured failures and model comparison work took priority. The evidence stages already had seeded-data, isolated-failure, and empty-retrieval tests, but no complete answer was evaluated.

**Tradeoff:** Completion requires a Report Writer, an endpoint, end-to-end cases, checks against gathered evidence, and a demo scenario. Reopen when the existing paths are sufficiently tested or investigation becomes the primary workflow. This continues [26](#decision-26) and [28](#decision-28).

<a id="46-closed-the-mixed-08-write-refusal-gap-with-a-one-sentence-prompt-fix"></a>
<a id="decision-46"></a>

### 46. State the write boundary in the analyze prompt

*2026-08-16*

**Decision:** I added an explicit write-boundary instruction and advanced the analyze prompt to v2.

**Why:** Sonnet had looked up an already-approved refund and answered “no further action needed.” The revised prompt passed `mixed-08` in three runs with no tools called; 19 related cases also passed.

**Tradeoff:** The earlier model-comparison reports remain evidence for v1. This check tested Sonnet's fix; it did not rerun the full Sonnet/Haiku comparison under v2.

**Evidence:** [Case study](CASE_STUDY.md).


<a id="47-first-ci-workflow-and-the-deterministic-eval-subset"></a>
<a id="decision-47"></a>

### 47. Run a deterministic evaluation subset in CI

*2026-08-16*

**Decision:** I added CI preparation for the database and corpus, followed by pytest and an 18-case evaluation subset.

**Why:** Refund rules, grounding, topic coverage, and mocked resilience cases make no live model calls. Permission cases can call Claude when access is allowed, so they were excluded.

**Tradeoff:** The subset cannot measure changing model behavior. Separate fixed-input SQL safety tests cover prohibited statements and cost limits. [48](#decision-48) records live calls still present in pytest.

**Evidence:** [CI workflow](.github/workflows/ci.yml).


<a id="48-pytest-still-needs-a-real-anthropic-key"></a>
<a id="decision-48"></a>

### 48. Record live model calls remaining in pytest

*2026-08-16*

**Decision:** I documented that some permission and endpoint tests still call Claude, and scoped the CI API key to the pytest step.

**Why:** Those tests exercise allowed requests through real endpoints. The deterministic evaluation step does not need the key.

**Tradeoff:** Pytest retains cost and external-service failure risk. Mocking those calls remains separate work.

<a id="49-verified-the-ci-gate-catches-a-regression-twice"></a>
<a id="decision-49"></a>

### 49. Verify both CI checks with an injected regression

*2026-08-16*

**Decision:** I changed the approval threshold from 20,000 to 200,000 cents on throwaway branches and ran the real PR workflow.

**Why:** The first trial failed the policy-drift test but skipped the later eval step. I added `if: ${{ !cancelled() }}` so the eval subset would also run. The second trial failed both the policy test and the manager-approval case.

**Tradeoff:** Both PRs were closed without merging. The change improved visibility into both checks; CI was already red after the first failure. It does not prove the checks detect every regression.

**Evidence:** [Policy drift test](apps/api/tests/test_refund_policy_drift.py).


<a id="50-verified-the-live-deployment-directly-found-two-real-gaps-the-evals-never-would-have-caught"></a>
<a id="decision-50"></a>

### 50. Exercise the deployed request paths

*2026-08-17*

**Decision:** I ran the live scenarios after CI and offline evaluations passed.

**Why:** A refund request extracted “2 Ergonomic Desk Chairs,” which failed to match “Ergonomic Desk Chair.” A suggested policy question also produced an unsupported-answer response under production embeddings.

**Tradeoff:** The refund cases bypassed extraction, and retrieval evaluations used the local provider. More cases through those same paths would leave these gaps intact. [51](#decision-51) fixed extraction; [52–53](#decision-52) investigated retrieval.

**Evidence:** [Deployment investigation](CASE_STUDY.md).


<a id="51-fixed-the-refund-extraction-bug-stop-folding-quantity-into-the-product-name"></a>
<a id="decision-51"></a>

### 51. Extract product names without quantity

*2026-08-17*

**Decision:** I changed the refund extraction field description to request the product name alone, with the failing chair request as an example.

**Why:** Two live endpoint checks returned the clean product name and `requires_manager_approval` under rule 6. An unaffected refund case still passed, and a live extraction test covered the reproduced failure.

**Tradeoff:** This remains model behavior with one known phrasing covered. The deterministic refund category still supplies pre-extracted fields.

**Evidence:** [Extraction regression test](apps/api/tests/test_refund_extraction.py).


<a id="52-recalibrated-the-rag-relevance-threshold-for-the-embedding-provider-production-runs"></a>
<a id="decision-52"></a>

### 52. Calibrate retrieval for the production provider

*2026-08-17*

**Decision:** I repeated the 18-question calibration with Voyage and selected 0.48, while retaining 0.46 locally.

**Why:** A relevant example at distance 0.4779 failed the local cutoff. The new production value retained relevant calibration examples but admitted 8 of 18 irrelevant candidates, compared with 3 of 18 locally.

**Tradeoff:** The original live question remained unresolved. Increasing retrieval depth also admitted more off-topic candidates. [53](#decision-53) then checked the exact query recorded in the live trace.

**Evidence:** [Provider thresholds](apps/api/app/rag/service.py).


<a id="53-closing-the-damaged-shipments-retrieval-gap-as-a-known-limitation"></a>
<a id="decision-53"></a>

### 53. Keep the production ranking failure visible

*2026-08-18*

**Decision:** I documented the unresolved “damaged shipments policy” query and changed the suggested prompt to a phrasing already verified in production.

**Why:** The exact traced query ranked rule 4 fourth at distance 0.6101 under Voyage, versus second at 0.4191 locally. The raw-question experiment in [52](#decision-52) had measured a different query.

**Tradeoff:** Changing the demo wording did not fix retrieval. The known phrasing still needs work, and threshold or retrieval-depth changes had not resolved it without other costs.

**Evidence:** [Recorded finding](evals/findings.md).


<a id="54-exposing-request_log_id-on-analyzeresponserefundevaluateresponse-so-the-ui-can-link-straight-to-a-trace"></a>
<a id="decision-54"></a>

### 54. Return request IDs for direct trace links

*2026-08-18*

**Decision:** I generated the log UUID before execution and returned `request_log_id` from analyze and refund responses.

**Why:** The UI needed to link each result to its request record. Response schemas and generated frontend types were updated together.

**Tradeoff:** The initial cache path replaced the original ID with the cache-hit ID. [55](#decision-55) reversed that choice. Trace access also needs an authorization policy before exposing customer data.

**Evidence:** [Analyze response schema](apps/api/app/orchestrator/schemas.py).


<a id="55-cache-hits-keep-the-original-requests-trace-reversing-54s-own-choice"></a>
<a id="decision-55"></a>

### 55. Link cached answers to their original trace

*2026-08-22*

**Decision:** A cached answer links to the request that originally produced it. The trace page identifies the answer as served from cache.

**Why:** Decision 54 linked to the cache-hit request, which showed zero tool calls and near-zero latency. That hid the evidence behind the answer.

**Tradeoff:** The cache hit still writes its own record, but the answer links to the earlier execution. Verification showed repeated questions returned the same original ID with tool calls and timing. This updates [54](#decision-54) for cached analyze responses only.

**Evidence:** [Cached analyze responses](apps/api/app/orchestrator/analyze_service.py).


<a id="56-measuring-llm-call-time-separately-from-tool-time-and-total-latency"></a>
<a id="decision-56"></a>

### 56. Measure model-call time directly

*2026-08-22*

**Decision:** I added `request_log.llm_latency_ms`, summed across covered analyze calls and refund extraction, including retry sleep.

**Why:** A 13-second request showed only 23ms of tool time. The remaining time had been labeled as model/orchestration time through subtraction. Direct measurement recorded 12,245ms of model time within 12,329ms total.

**Tradeoff:** Older rows have NULL and retain a derived fallback. Retry sleep remains included because the field measures elapsed time spent in the model-call path.

**Evidence:** [Request log schema](apps/api/app/db/observability_models.py).


<a id="57-moved-the-proxy-middleware-into-src-so-next-dev-runs-it"></a>
<a id="decision-57"></a>

### 57. Keep proxy middleware under src

*2026-08-23*

**Decision:** I moved the frontend proxy middleware into `apps/web/src/`.

**Why:** Local API requests returned 404 while production worked. In this layout, the development server discovered middleware under src; the build also accepted its former app-root location.

**Tradeoff:** The file retained the middleware.ts name. A fresh development server handled requests after the move, and the production build still registered the proxy. Moving to the newer proxy.ts convention remained separate work.

**Evidence:** [Frontend proxy](apps/web/src/middleware.ts).


<a id="58-a-landing-page-separate-from-the-scenario-demo"></a>
<a id="decision-58"></a>

### 58. Give the project a homepage before the scenarios

*2026-08-27*

**Decision:** I moved the demo to `/scenarios` and added an overview at `/` with results, architecture, and navigation.

**Why:** A visitor previously landed on scenario cards without an explanation of the project. The first homepage reused a captured injection example and read scores from committed results.

**Tradeoff:** The overview repeated some architecture content. Its highlight categories were curated, so the Evaluation Lab remained the place to inspect full coverage. [59](#decision-59) expanded the presentation.

**Evidence:** [Homepage](apps/web/src/app/page.tsx).


<a id="59-a-visual-pass-real-pre-run-snapshots-and-a-wider-landing-story"></a>
<a id="decision-59"></a>

### 59. Show captured results before a live run

*2026-08-30*

**Decision:** I added tabbed snapshots and scenario previews captured from actual application responses, alongside shared visual styling and navigation.

**Why:** Visitors could inspect an outcome before waiting for a model call. Stored snapshots suppress trace links because the demo database can reset; fresh runs return working links.

**Tradeoff:** Snapshots need recapture as time-sensitive data changes. The capture script retained a small duplicate test-client setup rather than adding an abstraction. This records the original visual pass, not a specification for all later page copy.

**Evidence:** [Snapshot capture](evals/capture_scenario_snapshots.py).


<a id="60-sourcing-the-ui-from-real-component-libraries-not-hand-rolling-it"></a>
<a id="decision-60"></a>

### 60. Use established UI components

*2026-08-30*

**Decision:** I used shadcn/ui for buttons, badges, and cards, and beUI for animated tabs. Source comments identify adaptations.

**Why:** Integrating the components exposed missing shared border styling. Color tokens were mapped to the site's theme, and card radius and shadows were adjusted to fit the existing design.

**Tradeoff:** Five runtime dependencies were added, with motion carrying weight for a small number of components. Unused candidate libraries contributed no code. This choice traded dependency cost for reusable component behavior.

**Evidence:** [UI components](apps/web/src/components/ui/).
