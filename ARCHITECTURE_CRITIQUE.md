# Architecture review

The original review read the design documents without prior project context, then checked their claims against the implementation. It identified ten findings. This document tracks what changed and what remains unresolved.

Status reviewed against repository code on **September 9, 2026**. This was a documentation and source review, not a new deployment test. [Architecture](ARCHITECTURE.md) describes the current system; the [decision log](DECISIONS.md) records the investigations and choices behind the changes.

## Where the findings stand

Finding numbers match the original review. Status applies to the specific issue, not the overall reliability of that component.

| # | Finding | Status |
|---|---|---|
| [1](#finding-1) | Flagged policy answers remain visible | Accepted for the demo |
| [2](#finding-2) | Missing customer details allowed a cross-customer lookup | Fixed for missing identifiers |
| [3](#finding-3) | Retrieval always returned the nearest passages | Threshold added; ranking gap remains |
| [4](#finding-4) | SQL safety checks missed incorrect calculations | Evaluation coverage added; live correctness remains limited |
| [5](#finding-5) | Tool-loop exhaustion produced an empty answer | Fixed |
| [6](#finding-6) | Copied policy constants could drift | Tests added for selected constants |
| [7](#finding-7) | Model calls lacked an explicit failure policy | Partially addressed |
| [8](#finding-8) | Refund evaluation used the full-access database connection | Fixed |
| [9](#finding-9) | Partial-quantity refunds are not modeled | Open |
| [10](#finding-10) | The system does not verify end-user identity | Open; backend perimeter added |

The original severity groups described an earlier implementation. They are omitted here because the remaining risks need assessment against the intended deployment. Verified identity and data isolation would be prerequisites for customer use.

## Findings and follow-up

<a id="finding-1"></a>

### 1. What happens when a policy answer is flagged?

**Original finding:** A small grounding badge was easy to miss beside a full answer. The design description also implied stronger enforcement than the check provided.

**Current behavior:** A prominent warning lists ungrounded claims above the answer. The answer remains visible. Citation matching checks whether named rules were retrieved; it cannot establish that the answer interpreted them correctly.

**Remaining risk:** A user can act on a flagged answer. Regeneration, withholding a recommendation, and escalation remain unimplemented. The warning is accepted for the demo, with those limits stated.

**Evidence:** [Decision 18](DECISIONS.md#decision-18), [answer rendering](apps/web/src/components/AnalyzeResult.tsx), and [grounding calibration](evals/groundedness_calibration.md).

<a id="finding-2"></a>

### 2. Can a refund request resolve to the wrong customer?

**Original finding:** When extraction returned no customer identifier, the lookup fell back to a product match across all customers.

**Current behavior:** Missing customer details return `could_not_process`. The product-only fallback was removed.

**Remaining risk:** A supplied name or email is not verified identity. The lookup also selects the most recent matching order item, so this fix does not resolve every ambiguity or establish permission to inspect that customer's order.

**Evidence:** [Decision 16](DECISIONS.md#decision-16) and [refund resolution](apps/api/app/orchestrator/refund_evaluator.py).

<a id="finding-3"></a>

### 3. Can retrieval return no supporting evidence?

**Original finding:** Retrieval returned the nearest passages even for unrelated questions. Citing one could then satisfy the grounding check.

**Current behavior:** A distance threshold filters retrieved candidates: 0.46 for local embeddings and 0.48 for Voyage. Retrieval can return no qualifying passages. The saved local comparison improved off-topic refusal from 0/15 to 12/15.

**Remaining risk:** Relevant and irrelevant passages overlap in distance. The threshold does not guarantee relevance or a refusal. One known production query, “damaged shipments policy,” still ranks the needed rule poorly.

**Evidence:** [Retrieval service](apps/api/app/rag/service.py), [experiment results](evals/ablation_table.md), and [Decision 53](DECISIONS.md#decision-53).

<a id="finding-4"></a>

### 4. Does valid SQL calculate the right answer?

**Original finding:** Execution checks restricted SQL access and cost but did not verify the calculation.

**Current behavior:** SQL evaluations compare returned values with independently calculated expectations. Those checks exposed calculation errors and guided a prompt change. Seven cases over three runs improved from 14/21 correct outcomes to 21/21.

**Remaining risk:** These assertions cover known evaluation questions. They are not a runtime correctness check for arbitrary user requests. An allowed query can still return a plausible wrong answer.

**Evidence:** [SQL calibration](evals/sql_semantic_calibration.md), [primary results](evals/primary_results.md), and [Decision 37](DECISIONS.md#decision-37).

<a id="finding-5"></a>

### 5. Does the tool loop report when it cannot finish?

**Original finding:** Exhausting the loop could return an empty answer that passed the citation check and appeared grounded.

**Current behavior:** The exhausted path returns `incomplete: true` with an explanation and skips grounding. Clients can distinguish this from a completed answer.

**Remaining risk:** Clients must handle the incomplete field. The response does not by itself explain why the model kept requesting tools; that requires inspecting the trace.

**Evidence:** [Decision 17](DECISIONS.md#decision-17) and [analyze service](apps/api/app/orchestrator/analyze_service.py).

<a id="finding-6"></a>

### 6. What catches a policy change that the code misses?

**Original finding:** Refund constants were copied from policy text with no test tying them back to it.

**Current behavior:** Tests compare selected policy values with evaluator constants, including reason windows, the approval threshold, and repeat-refund limits. A historical CI experiment deliberately changed the approval threshold and recorded failures in both the policy test and refund evaluation.

**Remaining risk:** The constants remain manually maintained. The tests match specific wording and cover selected rules; they do not establish complete agreement between prose and code.

**Evidence:** [Policy drift tests](apps/api/tests/test_refund_policy_drift.py) and [CI experiment](DECISIONS.md#decision-49).

<a id="finding-7"></a>

### 7. What happens when a model call stalls or fails?

**Original finding:** Calls lacked a shared, explicit timeout and retry policy. Slow synchronous requests could occupy the application's worker threads.

**Current behavior:** SQL generation and analyze calls use a wrapper with a 30-second timeout and one retry after two seconds for covered transient errors. Their services handle exhausted attempts with error or incomplete responses.

**Remaining risk:** Refund, ticket, and invoice extraction still call the SDK outside that wrapper, as do the investigation planner and evaluation judge. The work did not establish circuit breaking or isolation between workloads. The original “fixed for every call” status was too broad.

**Evidence:** [Retry wrapper](apps/api/app/llm_retry.py), [retry tests](apps/api/tests/test_llm_retry.py), and [Decision 38](DECISIONS.md#decision-38).

<a id="finding-8"></a>

### 8. How much database access does refund evaluation need?

**Original finding:** The evaluator used the same full-access connection as migrations and seeding.

**Current behavior:** It uses `refund_evaluator_readonly`, limited to its required tables. Customer email is available for resolution and excluded from the evaluator response.

**Remaining risk:** Correct role configuration still matters. The role limits database operations but does not establish which customer records a caller may access.

**Evidence:** [Restricted session](apps/api/app/db/refund_readonly.py) and [Decision 29](DECISIONS.md#decision-29).

<a id="finding-9"></a>

### 9. What if someone returns only part of an order line?

**Original finding:** The policy allows partial refunds, but the evaluator calculates the amount using the full line quantity.

**Current behavior:** The calculation remains `quantity × unit_price_cents`. Extraction has no field for the quantity being returned. Removing quantity from the product name fixed lookup behavior, not partial-refund support.

**Remaining risk:** Returning one of several units can be evaluated against the full amount, affecting manager-approval routing. Supporting this needs quantity extraction, validation against the purchased units, and appropriate cases.

**Evidence:** [Refund evaluator](apps/api/app/orchestrator/refund_evaluator.py), [extraction schema](apps/api/app/orchestrator/refund_extraction.py), and [refund policy](docs/policies/refund_policy.md).

<a id="finding-10"></a>

### 10. Who is allowed to use the customer data?

**Original finding:** The early API had no authenticated caller or deployed perimeter.

**Current behavior:** The backend checks a shared proxy secret, and CORS restricts browser origins. Tool permissions use a caller-set demo-role header. Those controls serve different purposes; none verifies the end user's identity.

**Remaining risk:** Real users need verified identity and access scoped to their organization and records. Refusing a missing customer identifier does not authorize requests that supply one. The current demo should not be treated as ready for customer data.

**Evidence:** [Proxy-secret middleware](apps/api/app/proxy_secret.py), [role checks](apps/api/app/permissions.py), and [Decision 23](DECISIONS.md#decision-23).

## How to use this review

Start with the remaining risk for the workflow you plan to change, then follow its evidence links. A completed fix closes a specific failure; it does not replace testing the surrounding request path.

The [case study](CASE_STUDY.md) follows the investigations. [EVALS.md](EVALS.md) describes what the current suite exercises and what it bypasses.
