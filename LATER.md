# Later

Near-term fixes first, ranked by evidence already in hand. Everything after the divider is a bigger extension, each deferred for a real reason.

## Record the model and prompt version per request

That information only lives in eval run metadata today. It never reaches the live request log, so a real production question can't be traced back to what produced it.

## Close the remaining RAG ranking gap

"Damaged shipments policy" still ranks the wrong passage first under the production embedding model. It's the sharpest concrete accuracy gap sitting in production right now.

## Mock the Anthropic client in the permission tests

`pytest` still needs a real API key to pass, because a few tests exercise live endpoints to confirm role checks. The fix is known and just hasn't happened yet.

---

## Model routing

Route simple SQL and RAG questions to a cheaper model, and keep Sonnet for the categories that carry financial or compliance risk. The eval data already shows exactly which categories need Sonnet's edge (`DECISIONS.md` #44). What's missing is the infrastructure to classify a question before the tool loop starts, real, unbuilt work for a category that only has 8 cases behind it right now. Build the classifier once that category has grown past a handful of cases.

## A reranker for RAG retrieval

The policy corpus holds 21 chunks today. A reranker solves a problem this corpus doesn't have yet. Once real policy documents land and retrieval starts surfacing plausible-but-wrong candidates worth sorting, this earns its place.

## A general row-level and column-level data policy

The SQL path blocks exactly one column, `customers.email`, hardcoded. That's the entire sensitive-data policy today, and every row is visible to any query the structural gate lets through. Part 1 runs one tenant and one dataset. Add a real policy layer the day a second tenant or a second sensitive column shows up.

## A dedicated prompt-injection defense

Today, prompt injection is a measured eval category, and the structural gate and the groundedness check already happen to catch every case in the current set. A layer built to defend against a known set of eval cases tends to fit those cases exactly, and a real attack rarely looks like one. This is worth building the moment a real attempt gets past the existing checks.

## Real authentication

Every request carries a role through a plain header today, which already tests the permission gate's real logic: the read/write split between roles. Real identity and session handling would stack a login system on top of a gate that's already proven with the header alone. Build it once real customer data enters the system.

## Finishing the investigation pipeline

`investigation_planner.py` and `data_analyst.py` already run a Planner-then-Data-Analyst pipeline against real seeded data (see `DECISIONS.md` #45). What's missing is the last stage, a Report Writer that turns gathered evidence into a synthesized answer, plus an endpoint to route a request through all three, eval cases for the full path, and a groundedness check on whatever the Report Writer produces. It's real, tested code, one stage short. It stays out of the near-term list because finishing it means new eval surface area, not just one more Claude call, and the measured core earned that attention first.
