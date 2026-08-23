# UI Specification

The UI is a portfolio surface for the Ops Intelligence Agent. Its job is to make the architecture legible: two tool paths (SQL, RAG), deterministic gates around a probabilistic core, and measured evidence that it works. Comprehension beats polish.

## Audiences

**Recruiter** (2 to 3 minutes). Needs to learn, without reading code: what the project does, why it is more than a chatbot (tool orchestration, guardrails, refusal behavior), and that there is evidence it works (real results, live traces). Served by: the Scenario Demo landing page's curated cards, the badge row on every result, and (once built) the Evidence view summary.

**Hiring manager** (10 to 20 minutes). Needs to learn: how a request flows through the workflow, which decisions are deterministic (structural gate, refund thresholds, approval routing) versus probabilistic (intent extraction, groundedness check), how failures surface (ungrounded claims, incomplete loops, rate limits, refusals), how the system is evaluated, and what tradeoffs were made. Served by: the Injection Attempt and Ambiguous Refund Refusal cards specifically, Execution Trace, and (once built) the Evidence view's full reports.

## Views

### 1. Scenario Demo (`/`, built) — primary landing page
- **Job:** Prove the architecture in one screen, without requiring the viewer to think of a question themselves.
- **Story:** As a recruiter, I want to run a curated scenario and see the actual result next to the behavior that was promised up front, so I can judge for myself whether the claim holds, in under a minute.
- **Components:** A static, hand-curated `SCENARIOS` array (`lib/scenarios.ts`) — no authoring UI. Five `ScenarioCard`s (data analysis, policy retrieval, refund approval, ambiguous refund refusal, injection attempt), each: name, one-sentence business context, a boxed "expected behavior" statement, a "Run scenario" button, and a result panel once run. Below the cards, a free-form refund request box (folded in from the former standalone Refunds page) for a viewer who wants to try their own input against the same deterministic gate.
- **Data:** `AnalyzeResponse` from `POST /api/query/analyze` (data-analysis and policy-retrieval cards) or `RefundEvaluateResponse` from `POST /api/refund/evaluate` (the other three cards, plus the free-form box). Result rendering is shared via `AnalyzeResult`/`RefundResult` components, also reused by `/ask` and the free-form box respectively.
- **States:** Idle: card shows only the setup (name/context/expected/button), no placeholder result. Loading: button reads "Running…", disabled. Error: red panel with message; 429 shows retry-after. Success: badge row + answer (analyze) or status badge + rule + reasoning + extracted fields (refund), plus a "View execution trace" link.
- **Navigation:** Each result's trace link goes to `/activity/{request_log_id}`. No other navigation on this page.

### 2. Ask (`/ask`, moved, secondary)
- **Job:** Demonstrate free-form, open-ended querying — for a viewer who wants to go beyond the curated scenarios.
- **Story:** As a hiring manager, I want to ask my own question and see the same gating and attribution the curated cards show, so I can confirm the behavior isn't cherry-picked.
- **Components:** `ExampleChip` row, textarea + submit, `AnalyzeResult` (badge row, warning panels, `Markdown` answer, sources, trace link).
- **Data:** `AnalyzeResponse` from `POST /api/query/analyze`. Rate-limit headers.
- **States:** Same as Scenario Demo's analyze path — loading/error/idle handled identically since both use `AnalyzeResult`.
- **Navigation:** Demoted out of the primary nav position (was `/`, now `/ask`, second tab). Reachable from `NavHeader` on every page.

### 3. Activity (`/activity`, unchanged)
- **Job:** Prove observability exists: every request is logged with latency, tokens, cost, and gate outcomes.
- **Story:** As a hiring manager, I want to scan recent requests and pick one worth inspecting, using cost and groundedness at a glance.
- **Components:** Table (time, type, latency, tokens, cost, grounded `Badge`, cached `Badge`), inline expandable trace per row (existing behavior, left as-is — not replaced by the new per-id route below).
- **Data:** `RequestLogRow[]` from `GET /api/observability/requests`.
- **States:** Loading: single "Loading…" line. Error: red panel with the failed path and status. Empty: "No requests logged yet."
- **Navigation:** Unchanged.

### 4. Execution Trace (`/activity/[id]`, built)
- **Job:** Reconstruct one request end to end on a single screen, addressable by a direct link.
- **Story:** As a hiring manager, I want to inspect one request and determine which tools ran, what evidence was used, which guardrails executed, and what the request cost, without searching through logs or source code.
- **Components:** Header (question, time, latency, tokens, cost, retry count), `Badge` row for gate outcomes (request type, grounded, cached), `ToolCallTrace` (sequenced calls with latency split between tools and LLM), retrieved RAG chunks (`rag_chunks_retrieved`) via `JsonPreview`, final output via `JsonPreview`.
- **Data:** `RequestLogDetailRow` from `GET /api/observability/requests/{id}` — the same endpoint Activity's inline expansion already used.
- **States:** Loading: "Loading trace…". Error: red panel (a 404 renders here; the "← Back to Activity" link above the heading is always present regardless of state, so a bad id never strands the viewer). Empty: `tool_calls` null or empty renders "No tool calls made for this request" (handled inside `ToolCallTrace`).
- **Navigation:** Back link to Activity. Linked from every Scenario Demo card result, from `/ask`, and from the free-form refund box.
- **Backend dependency, resolved:** `AnalyzeResponse`/`RefundEvaluateResponse` didn't expose their own `request_log` row's id. Added `request_log_id: uuid.UUID` to both schemas — see `DECISIONS.md` #54 for the full reasoning (in particular, why the analyze cache-hit path needed an explicit id override).

### 5. Evidence (`/evidence`, proposed, not yet built)
- **Job:** Present eval results as proof, not as claims.
- **Story:** As a recruiter, I want one screen stating what was measured and the headline numbers; as a hiring manager, I want the case counts, calibration method, and known failure modes behind them.
- **Components:** Short intro (`Markdown`), summary stat rows (case count, pass rate, groundedness calibration figures), then rendered report sections sourced from the committed eval reports (`evals/*.md`).
- **Data:** Build-time imports of committed eval artifacts. No fetch, no backend, no analytics infrastructure. Numbers update only when a new eval run is committed; state the run date on the page.
- **States:** Loading: none (static). Error: none at runtime; a missing artifact fails the build, which is the fail-loudly behavior we want. Empty: not applicable while artifacts are committed.
- **Navigation:** New "Evidence" tab in `NavHeader`. Deep links from the intro to the trace of a real logged request where one exists.

### 6. Architecture (`/architecture`, proposed, not yet built)
- **Job:** Show what the model decides and what the code decides, and say why, without a tour of the repo.
- **Story:** As a hiring manager, I want to understand which responsibilities belong to the model, which are enforced deterministically, and why the system was designed this way, without reading the entire repository.
- **Components:**

  **Part 1 — Architecture diagram.** `docs/img/architecture.svg`. The README reuses the same file.

  Flow, top to bottom: user request, agent/orchestrator loop, SQL tool or Policy/RAG tool, one deterministic enforcement seam, final response. The seam holds two chains side by side: the SQL chain (generated SQL, AST allowlist, cost gate, readonly DB role, audit) and the refund/actions chain (request, deterministic waterfall, draft, confirm, permission). A trace log branches off the orchestrator, the seam, and the final response.

  **Part 2 — Responsibility split.** The table answers one question: what decisions does this system delegate to probabilistic behavior? The model handles the parts that need flexibility, like reading free text, writing SQL, and interpreting policy language. Every row on the right is a real constraint. It runs independently of the model, and it guards one consequential action.

    | LLM proposes / interprets | deterministic systems enforce |
    |---|---|
    | tool selection | tool permissions (`require_permission` checks the calling role before any tool runs) |
    | candidate SQL | SQL AST allowlist (`validate_ast` checks tables, columns, and functions against an allowlist, and blocks bare `SELECT *`) |
    | request field extraction (refund reason, ticket category, pulled from free text) | query-cost limit (`check_cost` rejects a query whose `EXPLAIN` cost crosses a threshold, before it runs) |
    | policy interpretation (reading retrieved RAG chunks) | DB privilege boundary (the `ops_agent_readonly` role restricts columns and caps every query at a 5-second timeout, even if the checks above it fail) |
    | synthesis (turning SQL rows or RAG chunks into an answer) | refund waterfall (`evaluate_refund` runs a fixed rule sequence: return window, final-sale exemption, repeat-refund flag, $200 approval threshold) |
    | explanation (why the answer says what it says) | draft/confirm ticket lifecycle (`draft_support_ticket` creates a draft in memory, and a second call, `confirm_support_ticket`, under its own permission, writes it to the database) |
    | | groundedness check (`check_groundedness` matches cited rule numbers and titles against the chunks retrieved for that answer) |

  **Part 3 — Deliberately not built.** *(next)*

  **Part 4 — Decision links.** *(next)*

- **Data:** Static content: a committed SVG, and prose written from `ARCHITECTURE.md` and the enforcement code (`app/query/validation.py`, `app/query/service.py`, `app/permissions.py`, `app/orchestrator/refund_evaluator.py`, `app/tickets/service.py`, `app/orchestrator/groundedness.py`). Nothing is fetched at runtime.
- **States:** None. The page is static, and it follows the same fail-loudly rule as Evidence: a missing asset breaks the build.
- **Navigation:** A new "Architecture" tab in `NavHeader`, linking to the relevant `DECISIONS.md` entries for Part 4.

## Design constraints

Existing Tailwind setup and visual language only (current border/gray palette, `Badge` tones, table styles). Reuse `Badge`, `ToolCallTrace`, `Markdown`, `ExampleChip`, `JsonPreview`, and the new `AnalyzeResult`/`RefundResult`/`ScenarioCard`. The role selector moved out of `NavHeader` into a page-level `RoleFooter` (present on every page, below `<main>`) — it's supporting technical context, not the first thing a cold viewer sees. All views keep the strict loading / error / empty handling above; no silent fallbacks.

## Explicitly not building

Admin dashboard. Settings page. Advanced filtering or search on Activity. Custom design system or theme redesign. Animation work. New analytics infrastructure. A scenario-authoring UI (the curated set is a static array, edited by hand). Additional backend capabilities beyond the one `request_log_id` field the trace link needed.
