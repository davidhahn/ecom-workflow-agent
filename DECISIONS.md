1. packages/shared: generated-only, nothing hand-written
- The Win: Makes drift structurally impossible rather than procedurally discouraged. There's no hand-written type for the API contract to fall out of sync with, because there's no hand-written type at all. This is the thing that makes the monorepo decision in ARCHITECTURE.md actually pay off instead of being aspirational.
- The Tradeoff Accepted: Every backend schema change requires re-running codegen before the frontend will type-check against it. It's an extra step in the loop that a hand-written type wouldn't need, and one that's easy to forget mid-session and get a confusing stale-type error instead of a clear "run codegen" reminder.

2. docker-compose scope: database-only, no app services yet
- The Win: Keeps the compose file honest about what's actually verified: Postgres + pgvector boots and CREATE EXTENSION vector succeeds, full stop. Adding unverified app-service entries now would create a false impression of an integrated stack before the apps can actually talk to the DB.
- The Tradeoff Accepted: Local dev currently means running three things by hand (docker compose up, apps/api, apps/web) instead of one docker compose up. There are more manual steps every session until app services get added, in exchange for not lying to yourself about what's wired up.

3. SQLAlchemy + Alembic vs. raw SQL migrations
- The Win: Schema changes are versioned, reversible, and diffable in git. Autogenerate produces a migration file you can read and review, which matters for a portfolio project where the git history itself is part of what gets evaluated.
- The Tradeoff Accepted: Alembic's autogenerate doesn't always produce exactly the migration you'd hand-write (index ordering, constraint naming). This means migrations need a manual read-through before applying, and that review step is one more thing to remember to actually do rather than rubber-stamp.

4. Seed strategy: deterministic truncate-and-reinsert vs. randomized/faker-generated per run
- The Win: Idempotent and reproducible. The "60-day-late refund" and "80%-refund-rate product" edge cases are guaranteed to exist every time you run seed.py, which means eval cases written against specific rows won't silently break because a random seed generated different data on the next run.
- The Tradeoff Accepted: The dataset stays small and hand-curated rather than large and organically messy. You're trading the realism of a bigger, noisier dataset (closer to what a real ops team would query against) for the certainty that your specific edge cases are always present and discoverable.

5. SQL query path: four independent, differently-shaped safety layers
- The Win: Each layer catches a different failure class — the AST check (layer 1) catches obviously malicious/malformed queries before any DB round trip, the cost gate (layer 2) catches expensive-but-syntactically-valid queries, the Postgres role (layer 3) is a backstop that holds even if layers 1-2 have a bug, and the audit log (layer 4) makes every attempt — not just successes — inspectable after the fact. None of the four substitutes for another; a single combined validator would collapse these into one blind spot.
- The Tradeoff Accepted: More moving parts to reason about per request (Claude call → AST parse → EXPLAIN round trip → execution → audit write), and a slower request path than a single-layer check would have. Accepted because the whole point of layer 3 existing is to assume layers 1-2 are not infallible — collapsing them for speed would defeat the design.

6. Layer 3 column restriction: allowlist grant, not table-grant-then-revoke
- The Win: Verified empirically (not just written and trusted) that `GRANT SELECT ON customers` followed by `REVOKE SELECT (email) ON customers` is a **silent no-op** in Postgres — table-level and column-level SELECT are independent ACL entries, and a role with table-wide SELECT can still read a column whose column-level grant was individually revoked. Confirmed via `docker exec ... psql -U ops_agent_readonly` actually selecting `email` successfully despite the revoke having "run" without error. Fixed by granting SELECT only on the explicit non-email column list for `customers`, and table-wide SELECT for the other 5 tables (which have no columns to exclude). Re-verified: `SELECT email FROM customers` now fails with `permission denied`, all other columns and tables succeed.
- The Tradeoff Accepted: The customers table's grant statement has to be kept in sync by hand with `Customer`'s columns in `app/db/models.py` — if a new column is added there, the migration's `CUSTOMER_VISIBLE_COLUMNS` tuple needs a matching update, or the new column silently won't be selectable through the readonly role. This is a case where a hand-maintained list is safer than the theoretically-cleaner "grant broadly, revoke narrowly" approach, precisely because the latter fails silently rather than loudly.

7. RAG chunking: structural (per H2 / per rule), not fixed-size or semantic
- The Win: Each policy doc was hand-authored so that one H2 section = one self-contained rule, with no cross-section pronoun references (see `docs/policies/refund_policy.md`'s own intro). Chunking on that existing structure means chunk boundaries always land exactly on rule boundaries — no rule is ever split across two chunks or two rules merged into one, which a fixed-size or sliding-window chunker would risk doing arbitrarily. Rule number and source doc are preserved as chunk metadata precisely because the retrieval endpoint's job is to let a caller point back at "refund policy, rule 4," not just return a text blob.
- The Tradeoff Accepted: This chunker is coupled to the specific H2-per-rule structure of these three docs. It will silently produce wrong or missing chunks (or a `rule_number` that's off from the rule's real identity) if a future policy doc uses a different structure (e.g. H3 subsections, multiple rules under one H2). That's an acceptable coupling for a small, fixed, hand-authored corpus — it would not be for a corpus with heterogeneous document structure.

8. Local BAAI/bge-m3 embeddings instead of a hosted embedding API
- The Win: No external API dependency, no per-call cost, no network latency for a corpus this small (~17 chunks) — see the comment above the model init in `app/rag/embeddings.py`, which explicitly flags this as scope-specific rather than a default to keep unexamined.
- The Tradeoff Accepted: `sentence-transformers` pulls in `torch` and a multi-hundred-MB model download on first run, which is a heavy dependency for what's mechanically a very small lookup table right now. Also no ANN index (ivfflat/hnsw) on `policy_chunks.embedding` — an exact sequential scan is correct and fast at 17 rows, but that choice needs revisiting (both the index and possibly the local-vs-hosted embedding call) if the corpus grows into the thousands.

9. Groundedness check catches named citations, not just numeric ones
- The Win: The task's own example ("rule 9" vs "per the final-sale exclusion") makes clear a citation doesn't have to spell out a number. `groundedness.py` builds a title→rule_number map from the same chunker RAG ingestion uses (not a hand-duplicated list), normalizes hyphens/spaces, and checks the answer text against both forms. This caught a real case in testing: a `/query/analyze` answer described "Wrong Item Shipped" (rule 5's exact title) in detail — accurately, using knowledge implicit in the rule 9 chunk's own text — while the actual top-3 RAG retrieval for that request surfaced rules 9, 1, and 2, not 5. Numeric-only citation parsing would have missed this entirely and reported false groundedness.
- The Tradeoff Accepted: It's a substring heuristic, not comprehension — a title phrase used generically rather than as a citation could rarely false-positive, and a paraphrased rule description with neither the number nor the exact title will be missed (false negative, silently ungrounded). Accepted because the task specifically asked for structural checking, not an LLM judge; a second model call to verify citations would reintroduce exactly the non-determinism this check exists to avoid. Additionally, the check is deliberately calibrated to bias toward false positives over false negatives: a hypothetical answer that mentions "changed mind" generically (e.g. describing customer sentiment, not citing the rule) when rule 3 wasn't retrieved would get flagged even though nothing was really being cited — an acceptable cost, a reviewed-and-cleared flag. An actually-hallucinated citation getting marked grounded, by contrast, would silently undermine the one signal this endpoint gives a caller about whether to trust the answer — a materially worse failure. Given the check can't do content-level verification (only title/number matching), over-flagging is the safer of the two available error directions. (The rule 5/"Wrong Item Shipped" case in "The Win" above is a different thing: a *correct* flag — rule 5 genuinely wasn't retrieved for that request — not an example of this false-positive cost.)

10. Refund evaluator: sequential first-match-wins, not "repeat-flag overrides everything"
- The Win: Rule 7's own text ("regardless of the individual refund's reason code or amount") reads like it could override earlier checks, but read literally it's scoped to reason/amount specifically — not to a category exclusion or an expired time window, which are about the refund itself being invalid, not the customer's behavior pattern. Implemented as a strict ordered waterfall (category → time window → evidence → repeat-flag → threshold → approved) where the first rule that decisively applies wins; repeat-flag still runs "regardless of reason or amount" in the sense that it isn't skipped just because the reason is defective/wrong_item (unlimited window) or the amount is small — it just doesn't get a chance to fire if an earlier rule already denied the request.
- The Tradeoff Accepted: This is a judgment call the task didn't fully disambiguate. A customer already flagged for repeat refunds who submits a final-sale-excluded request gets `denied` (rule 9), not `flagged_for_review` (rule 7) — i.e., the more specific defect in this particular refund wins over the customer-level behavioral flag. If the intent was for the repeat-flag to be a hard override regardless of any other outcome, this needs revisiting.

11. `/refund/evaluate` extraction resolves order_item_id via DB lookup, not an LLM guess
- The Win: Claude extracts `product_identifier`/`customer_identifier` (free text) plus `reason` and a self-reported `reason_confident` flag; a plain SQL `ILIKE` lookup (`resolve_order_item`) does the actual resolution to a real `order_item_id`. Verified end-to-end against both seeded edge cases (Cotton Bath Towel Set, Last-Season Winter Jacket) and against an unresolvable product name and an ambiguous reason — both correctly return `could_not_process` instead of a guessed result. `could_not_process` isn't one of the task's four listed decision statuses; it was added because "reject/flag rather than guess" needs some representation, and the given output schema didn't have one.
- The Tradeoff Accepted: The `ILIKE` lookup takes the most-recent matching order_item with no disambiguation if a product name matches multiple order_items (e.g. across several orders) — for the two specified test products this doesn't matter (one is unique in the catalog, the other's outcome doesn't depend on which matching row is picked), but a general-purpose version of this would need the extraction step to also disambiguate by order ID or date when a customer references "the one I ordered last week."

12. Evidence-check outcome corrected from `pending` to `denied`
- The Win: The initial rule spec for the evidence check said damaged_shipping-without-evidence should return `pending` — but `pending` was never one of the task's four listed decision statuses (approved / denied / requires_manager_approval / flagged_for_review) in the first place, and more importantly implied a workflow (evidence arrives later, request gets re-evaluated) that Part 1 has no mechanism for: no evidence-upload endpoint, no persisted evaluation state, no trigger to re-run `evaluate_refund()` later. `evaluate_refund()` is a one-shot, stateless decision — there's nothing "pending" can resolve into on its own, so the only accurate answer when evidence is missing at evaluation time is that the refund can't be processed *now*, i.e. `denied`. Re-verified against both seeded edge cases after the change; the with-evidence case still approves correctly (unaffected — only the no-evidence branch changed).
- The Tradeoff Accepted: The `refunds.status` column's own CHECK constraint still allows `'pending'` as a stored value — that's unchanged and correct, since a human or a future workflow step could still legitimately set a real refund row to pending. Only the *evaluator's returned decision* stopped using it. (The seeded fixture row for this edge case, `app/db/seed.py`'s Cotton Bath Towel Set refund, was subsequently updated to `status='denied'` to match — that edit was made directly in seed.py, not by this evaluator change, since the evaluator never reads that row when scoring a new request.)

13. `rag_chunks_retrieved` needed `JSONB(none_as_null=True)`, not the plain type
- The Win: Verified empirically (not just written and trusted) that SQLAlchemy's `JSON`/`JSONB` column type defaults `none_as_null=False` — assigning a Python `None` to a nullable JSONB column serializes it as the JSON literal `null` (a real, non-NULL JSONB value) rather than mapping it to SQL `NULL`. Caught by checking `IS NOT NULL` directly in psql across all four request types after the first end-to-end verification pass: every `sql` and `refund_evaluate` row (neither of which touches RAG) showed `rag_chunks_retrieved` as non-NULL, containing the literal string `null`. Fixed by declaring the column `JSONB(none_as_null=True)`; re-verified the same way — `sql`/`refund_evaluate` rows now show genuine SQL `NULL`, `rag`/`analyze` rows show the actual chunk array.
- The Tradeoff Accepted: None really — this is a pure correctness fix, not a design tradeoff. Worth recording anyway because it's a non-obvious SQLAlchemy default that will bite again on any *future* nullable JSON/JSONB column in this codebase if `none_as_null=True` isn't set explicitly each time; there's no single place that defaults it project-wide.

14. Seed Data Uses Fixed Historical Dates, Not Time-Relative Offsets
- The Win: Deterministic, reproducible seed data (established in decision #4) — the same
  rows exist every time seed.py runs, so hand-verified edge cases stay findable and
  eval expected-values stay stable across re-seeds.
- The Tradeoff Accepted: Discovered while generating eval cases: every rule with a
  time-relative window (2, 3, 6's implicit recency assumptions, and especially 7's
  90-day trailing check) decays against fixed calendar dates as real time passes. Rule
  7 is already fully unreachable — no seeded refund falls within 90 days of "now" as
  of this writing — and this will only get worse, not resolve itself, the longer this
  project sits between demos or interviews. Not fixed as part of this eval-authoring
  pass since it's a seed-generation change, not an eval-case change; flagged here as a
  known, worsening gap. Fix path if revisited: compute time-relative seed fields
  (requested_at, order_date) as offsets from datetime.now() at seed-time rather than
  fixed dates, so edge cases stay evergreen regardless of when seed.py actually runs.

15. Groundedness Eval Cases: Reconciling JSON Fixtures with Typed Function Input
- The Win: `evals/cases.json` stores `retrieved_chunks` as plain JSON dicts (necessary,
  since JSON can't represent internal dataclass/Pydantic types), but `check_groundedness()`
  expects attribute access (`chunk.rule_number`), since it's typed as `list[RagChunkResult]`.
  This surfaced as a real `AttributeError: 'dict' object has no attribute 'rule_number'`
  when eval cases were first run against the live function rather than just
  schema-validated. Fixed by adding `chunk_from_dict()` next to `RagChunkResult` in
  `app/rag/schemas.py` — a single documented conversion path (`RagChunkResult(**data)`)
  other eval-loading code can reuse, rather than each caller inventing its own
  dict-to-object workaround (a `SimpleNamespace(**c)` shim was found already sitting
  untracked in `apps/api/tests/`, doing exactly that).
- The Tradeoff Accepted: `check_groundedness()` itself was deliberately left untouched —
  loosening it to accept dicts via `getattr`/`.get()` fallbacks would blur an
  already-correct type contract, and duck-typing appears nowhere else in this codebase.
  This is a small instance of a larger pattern worth watching as Part 4's eval runner gets
  built: any eval case whose expected input is a typed object, not a primitive or dict,
  needs this same reconciliation. Worth revisiting whether eval fixtures should store a
  schema hint or whether all internal functions consuming eval-fixture data should accept
  dict-like input by convention, rather than discovering each mismatch one broken test at
  a time.

16. Refund resolution requires a customer identifier — refusal, not a product-only fallback
- The Win: `resolve_order_item()` now refuses (returns `None` → `could_not_process`) rather
  than falling back to a product-only `ILIKE` match across the entire customer base when no
  customer identifier was extracted. Caught during an independent architecture critique
  (`ARCHITECTURE_CRITIQUE.md` finding #2) as a real correctness gap: because Part 1 has no
  session/identity concept, "no customer named in the request" is a common case, not an edge
  case, and the old fallback could render a real approve/deny decision against a completely
  different customer's order history. Verified end-to-end: a refund request naming no customer
  now returns `could_not_process` ("Could not identify which customer is making this
  request"), while the same request with a real customer name still resolves and evaluates
  correctly.
- The Tradeoff Accepted: This is a strict refusal, not a request for clarification — Part 1
  has no follow-up-question mechanism, so a request that's actually unambiguous (e.g.
  referencing a product only one customer has ever ordered) still gets refused if the customer
  wasn't named, since `resolve_order_item` has no way to know in advance that the product
  identifier alone would have been unique. Trades a small amount of legitimate-but-under-
  specified requests for eliminating the wrong-customer-match risk entirely — the right
  tradeoff given a wrong decision against the wrong customer is worse than an honest refusal.

17. Tool-loop exhaustion returns an explicit incomplete state, not a silently empty answer
- The Win: `analyze()`'s tool-call loop previously fell through to `answer = ""` if Claude was
  still requesting tools on the final allowed iteration (`MAX_TOOL_ITERATIONS` reached without
  ever hitting the loop's `break`) — and `check_groundedness("", [])` trivially returns
  `grounded=True` on empty input, so the failure rendered as a blank answer with a green
  "Grounded" badge and a 200 OK. Caught during the same independent critique (finding #5) as a
  direct violation of this project's own Fail Loudly rule. Fixed with Python's `for`/`else`:
  the `else` clause fires only when the loop completes all iterations without a `break`, an
  unambiguous signal distinct from "Claude decided it was done." That branch skips
  `check_groundedness()` entirely (nothing meaningful to check) and returns a new
  `incomplete: bool` field with an explanatory answer instead.
- The Tradeoff Accepted: `AnalyzeResponse.incomplete` is a new field older callers of this API
  don't know to check — defaulted to `False` to keep existing JSON consumers working without a
  hard break, but any caller that only reads `answer`/`grounded` and ignores `incomplete` is
  back to the same misleading-badge problem this fix exists to prevent. The incomplete-state
  message is also a fixed generic string, not a diagnostic of what Claude was actually still
  trying to do (which specific tool call, how many rounds) — enough to stop the silent
  failure, not enough to debug why it happened without checking `request_log` directly.

18. Groundedness warning made visually prominent, not gating
- The Win: the frontend previously rendered a full answer with equal visual weight to a small
  badge when `grounded: false` — easy to miss under time pressure, undercutting the point of
  having a groundedness signal at all. Caught during the same critique (finding #1: "the
  groundedness check doesn't gate anything"). Fixed on the display side only: a prominent
  bordered warning banner now renders above the answer whenever `grounded` is false, with
  `ungrounded_claims` listed explicitly rather than buried below in a small box.
- The Tradeoff Accepted: This is a visibility fix, not a gating fix — the answer is still
  shown in full, since Part 1 has no remediation flow (no re-generation, no escalation,
  nothing else to do with a flagged answer yet) and hiding it outright was explicitly out of
  scope. A user can still read past the banner and act on a flagged answer anyway; this makes
  that a harder mistake to make by accident, not an impossible one. The underlying
  groundedness heuristic's own known limitations (decision #9 — it can false-positive on a
  title phrase used generically) are unchanged; a more prominent banner around an
  already-imperfect signal is still built on that same imperfect signal.

---

**Note:** Decision #2 (docker-compose scope) is a direct consequence of the Part 1 scope boundary already recorded in `ARCHITECTURE.md`. Logged here separately because it's concrete enough to defend on its own, but if that upstream scope boundary changes, this entry needs to be revisited rather than treated as independent.
