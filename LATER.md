# Next steps

These are proposed priorities for the seeded demo, reviewed on September 12, 2026. Customer use would change the order: verified identity and data access must come before connecting customer records.

[Product scope](PRODUCT_SPEC.md) describes what is available today. The [architecture review](ARCHITECTURE_CRITIQUE.md) tracks remaining risks, and the [decision log](DECISIONS.md) preserves earlier choices.

## Improve the existing workflows

### 1. Record model and prompt versions on live requests

The live request log lacks this information, which makes failures harder to reproduce after a deployment. Evaluation runs already record their configuration, and SQL audit records carry a prompt version, but those do not provide a complete record for each live workflow.

Add the versions to request logs and expose them in System Traces. Verify that a fresh response and a cached response identify the configuration that produced the answer.

### 2. Evaluate retrieval with the production provider

The traced query “damaged shipments policy” ranks the relevant passage poorly under Voyage. The local evaluation uses a different embedding model, so its results do not validate production behavior. [Decision 53](DECISIONS.md#decision-53) records the unresolved case.

Run labeled questions through the production provider, including alternate phrasings and off-topic requests. Compare any retrieval change against that baseline and check for new false refusals or irrelevant passages. A working demo prompt alone would not close the gap.

### 3. Remove unintended live calls from permission tests

Some permission tests call Claude when verifying that an allowed request succeeds. That adds cost and model variance to a check about access.

Mock those model calls while keeping assertions on allowed and rejected roles. Keep live integration checks explicit and separate. Confirm the affected tests pass without a working model key.

### 4. Cover failures the current evaluations bypass

Refund-rule cases supply extracted fields, which concealed the quantity-in-product-name bug. The judge review also sampled only passing outcomes.

Add extraction examples based on live failures and human-labeled failing answers for judge validation. Expand SQL and combined-workflow coverage with independently checked expectations. New cases should exercise a missing behavior, rather than increase the count alone.

## Before a customer pilot

**Verify identity and scope data access.** Replace caller-set roles with verified identity. Define access to organizations, records, and sensitive fields, then test isolation before loading customer data. The proxy secret and the SQL email restriction do not provide that policy.

**Agree on the supported refund workflow.** The evaluator uses the full order-line quantity. Partial returns need quantity validation and prorated calculations if they belong in the pilot. Decide how staff should handle unresolved requests and flagged answers, including when a human must review a recommendation.

**Test attacks against the intended integrations.** Existing injection cases provide limited coverage, with some cases skipped. Review how untrusted text reaches extraction and tools, then test attempts to change fields or cross access boundaries. Add defenses based on those risks before deployment; a successful live attack should not be the trigger to start.

**Define outcomes and stop conditions.** Choose one workflow with the customer and measure its current handling time and correction rate. Begin with reviewed, read-only use. Agree on which failures stop the pilot and what evidence would justify expansion.

## Extensions that need more evidence

### Route some requests to a cheaper model

The [model comparison](evals/model_recommendation.md) found useful differences on the tested questions. It does not establish a routing policy for new traffic, and the shared analyze endpoint would need a way to classify requests before choosing a model.

Revisit routing when a broader comparison shows savings that justify classification errors, added latency, and maintenance. Evaluate with the current prompts; the historical comparison preceded the write-refusal fix.

### Add a retrieval reranker

The small corpus already has a ranking failure, so size alone is not a reason to dismiss reranking. A reranker could help when the correct passage appears among candidates but ranks too low.

Compare it against the production-provider baseline above. Keep it if it improves relevant-passage selection without unacceptable latency or regressions on other questions.

### Complete the investigation pipeline

The Planner and Data Analyst gather evidence and have direct tests. Finishing the workflow requires a Report Writer, an endpoint, evaluations for final answers, and checks against the gathered evidence. A demo surface would also need to show incomplete investigations clearly.

Reopen this work when an investigation workflow has a clear user need or becomes the project's primary demonstration. [Decision 45](DECISIONS.md#decision-45) records the original deferral and existing implementation.
