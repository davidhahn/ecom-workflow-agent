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
- The Tradeoff Accepted: `sentence-transformers` pulls in `torch` and a multi-hundred-MB model download on first run, which is a heavy dependency for what's mechanically a very small lookup table right now. Also no ANN index (ivfflat/hnsw) on `policy_chunks.embedding` — an exact sequential scan is correct and fast at 17 rows, but that choice needs revisiting (both the index and possibly the local-vs-hosted embedding call) if the corpus grows into the thousands. Resolved, but not for the reason anticipated above: the trigger that actually fired was deployment's memory constraint, not corpus growth — `torch`'s own import/allocation footprint was more than a memory-constrained deploy environment could absorb, independent of how small the corpus still is. `app/rag/embeddings.py` now dispatches on `EMBEDDING_PROVIDER` (`local` | `voyage`, default `local`): local dev keeps paying nothing (free, no network dependency, good for fast iteration) via the unchanged BAAI/bge-m3 path, while deploy sets `EMBEDDING_PROVIDER=voyage` and calls the hosted Voyage AI API instead, paying a per-call cost that's negligible at this corpus size (~17 chunks). Model chosen is `voyage-3.5-lite` at `output_dimension=1024`, an explicit pin (not left to a default) specifically so the output matches `policy_chunks.embedding`'s existing `vector(1024)` column with zero schema migration needed.

9. Groundedness check catches named citations, not just numeric ones
- The Win: The task's own example ("rule 9" vs "per the final-sale exclusion") makes clear a citation doesn't have to spell out a number. `groundedness.py` builds a title→rule_number map from the same chunker RAG ingestion uses (not a hand-duplicated list), normalizes hyphens/spaces, and checks the answer text against both forms. This caught a real case in testing: a `/query/analyze` answer described "Wrong Item Shipped" (rule 5's exact title) in detail — accurately, using knowledge implicit in the rule 9 chunk's own text — while the actual top-3 RAG retrieval for that request surfaced rules 9, 1, and 2, not 5. Numeric-only citation parsing would have missed this entirely and reported false groundedness.
- The Tradeoff Accepted: It's a substring heuristic, not comprehension — a title phrase used generically rather than as a citation could rarely false-positive, and a paraphrased rule description with neither the number nor the exact title will be missed (false negative, silently ungrounded). Accepted because the task specifically asked for structural checking, not an LLM judge; a second model call to verify citations would reintroduce exactly the non-determinism this check exists to avoid. Additionally, the check is deliberately calibrated to bias toward false positives over false negatives: a hypothetical answer that mentions "changed mind" generically (e.g. describing customer sentiment, not citing the rule) when rule 3 wasn't retrieved would get flagged even though nothing was really being cited — an acceptable cost, a reviewed-and-cleared flag. An actually-hallucinated citation getting marked grounded, by contrast, would silently undermine the one signal this endpoint gives a caller about whether to trust the answer — a materially worse failure. Given the check can't do content-level verification (only title/number matching), over-flagging is the safer of the two available error directions. (The rule 5/"Wrong Item Shipped" case in "The Win" above is a different thing: a *correct* flag — rule 5 genuinely wasn't retrieved for that request — not an example of this false-positive cost.) A second instance surfaced during prompt-injection testing (case 06, fabricated-rule-number attack): the model correctly refused to affirm a nonexistent rule 15, but the check flagged the refusal itself as ungrounded, since its literal-match logic can't distinguish a citation from a mention-in-denial. Confirms the same tradeoff, not a new gap.

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

19. Test isolation requires explicitly importing every model module, not just the one under test
- The Win: `tests/test_tickets.py` failed with `sqlalchemy.exc.NoReferencedTableError` on
  `RequestLog.sql_query_audit_id -> query_audit_log.id` when run in isolation (`pytest
  tests/test_tickets.py`), despite passing inside the full suite. Root cause: SQLAlchemy
  resolves a string-based `ForeignKey(...)` lazily, against whatever tables have actually been
  imported into `Base.metadata` at the time any ORM write triggers mapper configuration — and
  that configuration step covers every pending mapper at once, not just the table being
  written to. `audit_models.py`/`observability_models.py`/`rag_models.py` each register their
  own table only as a side effect of being imported somewhere; nothing in `test_tickets.py`'s
  own import chain happened to pull in `audit_models`, so `query_audit_log` was never
  registered, and configuring *any* mapper (here, inserting a `SupportTicket`) failed on a
  wholly unrelated table's dangling FK. The project already had the fix pattern —
  `alembic/env.py` imports `audit_models`/`rag_models`/`observability_models` explicitly with
  `# noqa: F401` specifically for this reason — it just wasn't applied to the test suite.
  Fixed by adding the same three imports to `tests/__init__.py`, so every test file gets the
  full metadata registered regardless of which tables its own imports happen to touch.
- The Tradeoff Accepted: This is a real, generalizable gap, not a one-off — any *new* model
  module added later (the next `db/*_models.py` file) needs the same import added to
  `tests/__init__.py`, or isolated runs of unrelated test files can fail again with the same
  confusing error, pointing at a table the failing test never touches. There's no compile-time
  or lint-time guard against forgetting this; it will only surface again as a runtime failure
  in whichever test happens to be unlucky enough to run first in isolation. Worth revisiting if
  the project ever adds a lint rule or a single `app.db.all_models`-style import module both
  `alembic/env.py` and `tests/__init__.py` pull from, so there's one place to update instead of
  two.

20. Permission enforcement v1: one dependency, keyed by tool_name against the registry, not by endpoint
- The Win: `require_permission(tool_name, request_type)` is a single FastAPI dependency
  factory, reused on every gated route, that looks up `TOOLS[tool_name].permission_required`
  from the tool registry and checks it against a demo role read from the `X-Demo-Role` header
  (fails closed to `read_only_viewer` on a missing/invalid header — never open access).
  Keying the check by `tool_name` rather than by endpoint or a role-tier string comparison is
  what makes `support_agent` able to call `draft_support_ticket`
  (`permission_required="read_only"`) but not `confirm_support_ticket`
  (`permission_required="write"`), even though both endpoints are conceptually "the ticket
  workflow" and a naive per-route or per-workflow check would have conflated them. This is the
  actual payoff of the tool registry existing at all (see the `exposed_to_analyze` /
  `anthropic_tool_defs()` split from the shipments-tool pass): a second system
  (permissions) reads the same single source of truth a third system (the Claude-facing tool
  list) already reads, instead of each maintaining its own parallel notion of what a tool is
  allowed to do. Denials still write a `request_log` row (role, required permission, and the
  raw request body) even though they short-circuit before the route handler's own
  `request_log_span` ever opens — logged directly from inside the dependency instead.
- The Tradeoff Accepted: `X-Demo-Role` is a client-supplied, unauthenticated header — any
  caller can claim `admin` by setting it themselves. Explicitly fine for this pass (real auth
  is a separate, later step per the task), but this means "permission enforcement v1" enforces
  a role the caller asserts about themselves, not one the system verifies. `/refund/evaluate`
  and `/query/analyze` are both unprotected by this dependency — `/refund/evaluate` because it
  was never registered in the tool registry in the first place (this dependency has nothing to
  look up `permission_required` from without a `TOOLS` entry), and `/query/analyze` by explicit
  scope (it doesn't currently call any write-tier tool). Both are real, currently-open gaps,
  not oversights — they're the next things to close, not this pass's job.

21. Vendor invoice draft/confirm: a confirm-time duplicate refuses the write, it doesn't insert a 'duplicate' row
- The Win: The task spec (schema-first) put a real unique index on `vendor_invoices (vendor_name, invoice_number)`, then separately asked for a `status = 'duplicate'` value and for the duplicate check to be "re-run one more time at confirm-time... inserts into vendor_invoices with whatever status/flagged_reasons the validation produced." Taken completely literally, those two requirements collide: a second row for a pair that's already in the table is exactly what the unique index exists to reject, so an insert attempt with `status='duplicate'` raises `IntegrityError` — caught in testing (`test_duplicate_submitted_between_draft_time_and_confirm_time_caught_at_confirm`) before it ever reached a real deployment. Resolved by reading "do not let a duplicate slip through even if every other check passes" as the controlling sentence: a confirm-time duplicate now short-circuits before any insert is attempted and returns a structured `status: "error"` with `validation_status: "duplicate"` and an explanatory `error_reason`, mirroring exactly how a missing/expired draft_id is already reported — never a raised exception, per this tool's own registered `error_behavior`. `draft_vendor_invoice`/`confirm_vendor_invoice` otherwise reuse `draft_support_ticket`/`confirm_support_ticket`'s mechanism verbatim: same in-memory dict-plus-lock draft store shape (10-minute TTL, a confirmed draft is marked not deleted, so a retried confirm is idempotent), same `requires_confirmation` gate re-read from the registry at call time, same `read_only`/`write` permission split.
- The Tradeoff Accepted: A `status='duplicate'` row is now something `validate_invoice()` (draft-time) can return in its response but that literally never gets persisted as its own row in `vendor_invoices` — the column's own CHECK constraint allows a value no code path ever actually inserts. That's an honest reflection of the unique index making a persisted duplicate row a contradiction in terms, not a bug, but it does mean the `status` CHECK constraint is slightly wider than what confirm_invoice can ever write, which would read as strange to someone auditing the schema without this entry. Only the duplicate check (not the full arithmetic/date/confidence validation) is re-run at confirm-time, on the reasoning that those other checks were computed against the same already-extracted fields and can't change between draft and confirm — this is deliberately narrower re-validation than draft-time, and would need revisiting if a future field became time-dependent (e.g. a confidence threshold that changes over time).
- Follow-up, closed: `vendor_invoices` never getting a row for a rejected duplicate (see above) means `request_log` is the *only* audit trail a human has for investigating a duplicate-confirm attempt — so it was checked directly, not assumed. Pulled the actual row `/invoices/confirm` writes on a duplicate rejection and found `output` held only `{status, invoice_id, validation_status, flagged_reasons, error_reason}`; `vendor_name`/`invoice_number` were present only as prose embedded inside `error_reason`, and `invoice_date`/`subtotal_cents`/`tax_cents`/`total_cents`/`line_items` weren't there at all — confirmed thin, not sufficient to actually investigate an attempt from `/observability/requests` alone. Also checked a *successful* confirm's logged `output` for comparison and found it equally thin (`InvoiceConfirmResponse` never carried those fields either) — so "same level of detail as a successful confirm" was aspirational, not yet true. Fixed by having `confirm_invoice()` log a dict that merges the API response with the full extracted fields off the draft record (`vendor_name`, `invoice_number`, `invoice_date`, `subtotal_cents`, `tax_cents`, `total_cents`, `line_items`, `field_confidence`) on every branch that has a `record` to draw from — success, idempotent retry, and duplicate rejection alike — not just the duplicate case, so the three outcomes are actually logged at a consistent level of detail instead of only the newly-fixed one being richer than the pre-existing "working" ones. Verified against a real row: `SELECT output FROM request_log WHERE request_type='invoice_confirm' AND output->>'validation_status'='duplicate'` now returns vendor, invoice number, date, and all three cent amounts as structured JSON keys, not prose. Covered by `test_duplicate_confirm_rejection_is_logged_with_full_invoice_detail`, which queries `request_log` directly and asserts on the individual field values, not just that a row with the right `request_type` exists.

22. Tool-call tracing: `tool_calls` is NULL for every request type except 'analyze', and never NULL for that one
- The Win: `request_log.tool_calls` (new JSONB column) exists purely because `/query/analyze`'s tool-call loop is the one code path in the system that can make an unbounded, ordered sequence of sub-calls within a single request — every other request type (`sql`, `rag`, `ticket_draft`, `invoice_draft`, ...) makes at most one LLM call, so the concept of "a trace" doesn't apply to them at all, not just "doesn't apply this time." That distinction is enforced structurally, not just documented: `analyze()` sets `log.tool_calls` on *every* return path — the cache-hit short-circuit, the `MAX_TOOL_ITERATIONS`-exhaustion branch, and the normal completion path — always to a real (possibly empty) list, never left unset. Every other request type's `request_log_span` caller never touches `tool_calls` at all, so `LogFields`'s dataclass default (`None`) is what actually gets written for them. The two states mean different things: `NULL` = "this request type has no notion of a tool-call trace," `[]` = "traced, and zero tools were called" (e.g. Claude answered directly, or the answer was served from cache). Collapsing those into one would make an analyze row that legitimately called no tools indistinguishable from a `sql` row where the column just isn't meaningful. Verified against a real `/query/analyze` call using both `run_sql_query` and `search_policy`: the persisted `tool_calls` array had two entries in call order (`sequence` 0 and 1), each carrying the tool's real input, real output, and a real per-call `latency_ms` (112ms for the SQL call, 3554ms for the RAG call in that run) — not fabricated after the fact from the final response, but appended immediately after each individual tool call completes, which is also what makes the `MAX_TOOL_ITERATIONS`-exhaustion case safe: the array is only ever built from fully-formed entries, so a request cut off mid-loop still logs a valid, readable partial trace instead of a broken structure.
- The Tradeoff Accepted: `sequence` is a strictly increasing counter across the *whole* loop (`len(tool_calls)` at append time), not reset per turn — correct for today's sequential dispatch (each tool_use block in a turn is executed and appended to the list one at a time, in the order Claude's response listed them), but it would need revisiting if tool calls within a turn were ever dispatched concurrently, since `sequence` would then record append-order rather than a true causal order. `latency_ms` per call is wall-clock time around that one tool's dispatch function only (`_run_run_sql_query_tool`/`_run_search_policy_tool`) — it does not include the JSON-encoding of the tool_result or Claude's own per-turn processing time, both of which land in the "remaining (LLM thinking / orchestration)" figure the frontend derives as `total_latency_ms - sum(call latencies)`. That derived figure is therefore an upper bound on actual "thinking" time, not a precise measurement — it also silently absorbs network/serialization overhead from every Claude API round trip in the loop, so a request with many small tool calls will show more "thinking" time than one with few large ones purely from that overhead, not from Claude actually reasoning longer. `GET /observability/requests/{id}`'s `RequestLogDetailRow` is `RequestLogRow` subclassed with `tool_calls` added, not a field-for-field duplicate — chosen specifically so the list endpoint's existing `response_model=RequestLogRow` (unchanged) structurally cannot serialize `tool_calls` into a list response no matter what the ORM row underneath carries, which is what "the list stays summary-only" actually rests on: not a convention someone has to remember, but a field that only exists on the subclass the list endpoint never uses.

---

**Note:** Decision #2 (docker-compose scope) is a direct consequence of the Part 1 scope boundary already recorded in `ARCHITECTURE.md`. Logged here separately because it's concrete enough to defend on its own, but if that upstream scope boundary changes, this entry needs to be revisited rather than treated as independent.
