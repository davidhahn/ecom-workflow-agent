# UI Specification

The UI is a portfolio surface for the Ops Intelligence Agent. Its job is to make the architecture legible: two tool paths (SQL, RAG), deterministic gates around a probabilistic core, and measured evidence that it works. Comprehension beats polish.

## Audiences

**Recruiter** (2 to 3 minutes). Needs to learn, without reading code: what the project does, why it is more than a chatbot (tool orchestration, guardrails, refusal behavior), and that there is evidence it works (real results, live traces). Served by: the landing page's hero and proof snapshot, the Scenarios page's curated cards, the badge row on every result, and (once built) the Evidence view summary.

**Hiring manager** (10 to 20 minutes). Needs to learn: how a request flows through the workflow, which decisions are deterministic (structural gate, refund thresholds, approval routing) versus probabilistic (intent extraction, groundedness check), how failures surface (ungrounded claims, incomplete loops, rate limits, refusals), how the system is evaluated, and what tradeoffs were made. Served by: the Injection Attempt and Ambiguous Refund Refusal cards specifically, Execution Trace, and (once built) the Evidence view's full reports.

## Views

### 1. Landing (`/`, built, primary entry point)
- **Job:** Tell a visitor who's never seen this before what it is, fast, and point them at something they can run themselves.
- **Story:** As a recruiter with no context, I want the first screen to tell me plainly what this project does, so I can decide if it's worth two more minutes before I click anything.
- **Components:** Hero (eyebrow, `h1`, two-sentence pitch, three capability badges, a primary CTA into `/scenarios`, a GitHub link, then a stat strip of three pills linking to Evaluation Lab, Architecture, and Activity). `InjectionSnapshot`: the same pre-run injection-attempt result the old root page used, now its own component, linking out to run it live on `/scenarios`. A "How it works" section (three short steps, plus the architecture diagram). A "What the evals actually show" section with four hand-picked eval-category stat cards and a line naming whichever ones are still short of 100%. An "Explore" grid, one card per other page, each with that page's job in a sentence.
- **Data:** `getEvalResults()` and `RESPONSIBILITY_ROWS` (`lib/architecture.ts`). Same static, build-time sources the old page used. No number here gets typed in by hand.
- **States:** None. The page renders statically on the server, under the same fail-loud rule as Evaluation Lab and Architecture. A missing eval artifact breaks the build. It never renders a wrong number instead.
- **Navigation:** CTA into `/scenarios`. The explore grid links out to all five other pages. `IntroBanner` shows up on every other route but hides here, since this page already covers the same ground, at more length.

### 2. Scenarios (`/scenarios`, built, moved from `/`)
- **Job:** Prove the architecture in one screen, without requiring the viewer to think of a question themselves.
- **Story:** As a recruiter, I want to run a curated scenario and see the actual result next to the behavior that was promised up front, so I can judge for myself whether the claim holds, in under a minute.
- **Components:** A static, hand-curated `SCENARIOS` array (`lib/scenarios.ts`) — no authoring UI. Five `ScenarioCard`s (data analysis, policy retrieval, refund approval, ambiguous refund refusal, injection attempt), each: name, one-sentence business context, an "expected behavior" statement collapsed behind a native `<details>` (it opens automatically once a result exists, which is the moment the promise can be compared against what happened), a "Run scenario" button, and a result panel once run. Below the cards, collapsed behind its own `<details>`: a free-form refund request box (folded in from the former standalone Refunds page) for a viewer who wants to try their own input against the same deterministic gate.
- **Data:** `AnalyzeResponse` from `POST /api/query/analyze` (data-analysis and policy-retrieval cards) or `RefundEvaluateResponse` from `POST /api/refund/evaluate` (the other three cards, plus the free-form box). Result rendering is shared via `AnalyzeResult`/`RefundResult` components, also reused by `/ask` and the free-form box respectively.
- **States:** Idle: card shows only the setup (name, context, the collapsed expected-behavior row, button), no placeholder result. Loading: button reads "Running…", disabled. Error: red panel with message; 429 shows retry-after. Success: badge row + answer (analyze) or status badge + rule + reasoning + extracted fields (refund), plus a "View execution trace" link.
- **Navigation:** Each result's trace link goes to `/activity/{request_log_id}`. No other navigation on this page.

### 3. Ask (`/ask`, moved, secondary)
- **Job:** Demonstrate free-form, open-ended querying — for a viewer who wants to go beyond the curated scenarios.
- **Story:** As a hiring manager, I want to ask my own question and see the same gating and attribution the curated cards show, so I can confirm the behavior isn't cherry-picked.
- **Components:** Textarea + submit first, then an `ExampleChip` row collapsed behind a `<details>` ("Not sure what to ask? Try an example") below the form. The textarea's placeholder already shows one inline example, so the chips can wait for a second click. `AnalyzeResult` (badge row, warning panels, `Markdown` answer, sources, trace link).
- **Data:** `AnalyzeResponse` from `POST /api/query/analyze`. Rate-limit headers.
- **States:** Same as Scenarios's analyze path — loading/error/idle handled identically since both use `AnalyzeResult`.
- **Navigation:** Demoted out of the primary nav position (was `/`, now `/ask`, second tab). Reachable from `NavHeader` on every page.

### 4. Activity (`/activity`, unchanged)
- **Job:** Prove observability exists: every request is logged with latency, tokens, cost, and gate outcomes.
- **Story:** As a hiring manager, I want to scan recent requests and pick one worth inspecting, using cost and groundedness at a glance.
- **Components:** Table (time, type, latency, cost, grounded `Badge`, cached `Badge`). Every row links to that request's Execution Trace page. The time cell carries the real anchor for keyboard and middle-click, and the whole row is clickable for everyone else. The old inline per-row expansion is gone: it only ever covered `analyze` rows, and the per-id page shows the same trace with more context. Token counts moved off this table to the per-id page too. The story here is "pick a request worth inspecting, using cost and groundedness at a glance," and tokens belong to the inspection.
- **Data:** `RequestLogRow[]` from `GET /api/observability/requests`.
- **States:** Loading: single "Loading…" line. Error: red panel with the failed path and status. Empty: "No requests logged yet."
- **Navigation:** Every row opens `/activity/{id}`.

### 5. Execution Trace (`/activity/[id]`, built)
- **Job:** Reconstruct one request end to end on a single screen, addressable by a direct link.
- **Story:** As a hiring manager, I want to inspect one request and determine which tools ran, what evidence was used, which guardrails executed, and what the request cost, without searching through logs or source code.
- **Components:** Header (question, time, latency, tokens, cost, retry count), `Badge` row for gate outcomes (request type, grounded, cached), `ToolCallTrace` (sequenced calls with latency split between tools and LLM), and one collapsed "Raw request log data" `<details>` holding both the retrieved RAG chunks (`rag_chunks_retrieved`) and the final output, each via `JsonPreview`.
- **Data:** `RequestLogDetailRow` from `GET /api/observability/requests/{id}`.
- **States:** Loading: "Loading trace…". Error: red panel (a 404 renders here; the "← Back to Activity" link above the heading is always present regardless of state, so a bad id never strands the viewer). Empty: `tool_calls` null or empty renders "No tool calls made for this request" (handled inside `ToolCallTrace`).
- **Navigation:** Back link to Activity. Linked from every Scenarios card result, from `/ask`, from the free-form refund box, and from every Activity row.
- **Backend dependency, resolved:** `AnalyzeResponse`/`RefundEvaluateResponse` didn't expose their own `request_log` row's id. Added `request_log_id: uuid.UUID` to both schemas — see `DECISIONS.md` #54 for the full reasoning (in particular, why the analyze cache-hit path needed an explicit id override).

### 6. Evaluation Lab (`/evaluation-lab`, proposed, not yet built)
- **Job:** Show a reader the real eval numbers and where each one came from.
- **Story:** As a recruiter, I want one screen with the headline pass rates. As a hiring manager, I want the case counts and the environment behind each number, plus the calibration work underneath.
- **Components:** A headline pass-rate stat and a one-line environment strip (model, judge, dataset version, commit, cache flag, run id) read from the latest committed `experiment.json`. A per-category table read from that same run's `results.json`, one row per category with `n`, pass/fail, and the pass rate the file already computed. The recruiter's read ends there. Below the table, collapsed by default behind native `<details>`: a fuller run-details block (the same environment fields plus skipped categories and cases), then the six committed eval reports in order (`frozen_suite.md`, `primary_results.md`, `experiment_history.md`, `measurement_context.md`, `findings.md`, `methodology.md`), each with a one-line hook on its collapsed row so a hiring manager can pick what to expand.
- **Data:** `evals/results/20260822-201944/results.json` and its sibling `experiment.json`, plus the six `evals/*.md` files, all read server-side at render time (`apps/web/src/lib/evals.ts`). Every number on the page is a field already computed in a committed file, displayed with its original denominator intact.
- **States:** Loading: none, the page is static. Error: none at runtime. A missing or malformed source file throws during `next build`, so a bad artifact fails the build before it can render a wrong page.
- **Navigation:** New "Evaluation Lab" tab in `NavHeader`.

### 7. Architecture (`/architecture`, proposed, not yet built)
- **Job:** Show what the model decides and what the code decides, and say why, without a tour of the repo.
- **Story:** As a hiring manager, I want to understand which responsibilities belong to the model, which are enforced deterministically, and why the system was designed this way, without reading the entire repository.
- **Components:**

  **Part 1 — Architecture diagram.** `docs/img/architecture-diagram.svg`. The README reuses the same file.

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

  **Part 3 — Deliberately not built.** Every one of these is a tool I know how to use. Each one stayed out for a specific reason. On the page, each entry's title stays visible and its reasoning sits behind a native `<details>`, so the list scans in six lines.

  - **Multi-agent decomposition.** A Planner and a Data Analyst module already exist, tested and working. No endpoint routes a live request through them, because the measured workflow never turned up a problem only a third agent could fix. Every additional agent is more latency, and one more thing that can break.
  - **A workflow framework (LangGraph or similar).** The orchestration today is one direct call to the Anthropic SDK, with a single bounded retry. It's small enough to read start to finish in one sitting. A framework migration would change the plumbing, and leave every failure the evals have found exactly where it is.
  - **A vector database migration, or a reranker.** The policy corpus holds 21 chunks in Postgres, through pgvector. That's the whole search space. One real retrieval problem turned up during evals, and calibrating the relevance threshold per embedding provider traced it and mostly fixed it.
  - **Production OAuth or a full identity system.** Every request carries a demo role through a header. The docs call it that, plainly, right on the page. Real authentication would prove a skill this project already shows somewhere else.
  - **A second agentic investigation workflow.** The error analysis after the first eval run pointed somewhere else: a write-refusal bug, and eval categories too small to trust yet. Those won, so the Report Writer stage never got built, the piece that would have turned the Planner and Data Analyst's findings into a real answer. Both modules still only run from tests.
  - **More UI surface.** The interface has one job: put real evidence in front of a reader. An admin dashboard or a settings page would turn it into something else, a full operations product, which was never the goal here.

  **Part 4 — Decision links.** Five entries from `DECISIONS.md`, picked for what each one reveals about how a call got made.

  - **Why SQL safety runs on four separate layers** (`DECISIONS.md` #5). A mistake that slips past one check has three more chances to get caught.
  - **Where the groundedness check still lets a lie through** (`DECISIONS.md` #32). It checks whether a rule number showed up in what got retrieved, and stops there, so a wrong claim attached to a real number slips past clean.
  - **A judge grading itself, caught before it ran** (`DECISIONS.md` #41). The judge and the app under test read the same model env var, so swapping the model under test would have swapped the judge too.
  - **Haiku was cheaper, and it stayed on the bench** (`DECISIONS.md` #44). It matched Sonnet almost everywhere, and lost the cases that carry the real cost: refund totals, compliance verdicts.
  - **The pipeline that works and has nowhere to run** (`DECISIONS.md` #45). Error analysis pointed at bugs in the measured core first, and a third agent lost to that ranking.

- **Data:** Static content: a committed SVG, and prose written from `ARCHITECTURE.md` and the enforcement code (`app/query/validation.py`, `app/query/service.py`, `app/permissions.py`, `app/orchestrator/refund_evaluator.py`, `app/tickets/service.py`, `app/orchestrator/groundedness.py`). Nothing is fetched at runtime.
- **States:** None. The page is static, and it follows the same fail-loudly rule as Evidence: a missing asset breaks the build.
- **Navigation:** A new "Architecture" tab in `NavHeader`, linking to the relevant `DECISIONS.md` entries for Part 4.

## Design constraints

Existing Tailwind setup and visual language only (current border/gray palette, `Badge` tones, table styles). Reuse `Badge`, `ToolCallTrace`, `Markdown`, `ExampleChip`, `JsonPreview`, and the new `AnalyzeResult`/`RefundResult`/`ScenarioCard`. There's no role picker anywhere in the UI. The role stays pinned to `read_only_viewer` through `RoleProvider`, and `setRole` is never called. That's fine for now: neither `/query/analyze` nor `/refund/evaluate` checks the role at all, and the tool-backed endpoints that do check it (tickets, invoices, direct SQL) aren't wired into any page yet. A role picker would be UI with nothing behind it. Build one only once a page actually calls a role-gated endpoint. All views keep the strict loading / error / empty handling above; no silent fallbacks.

## Explicitly not building

Admin dashboard. Settings page. Advanced filtering or search on Activity. Custom design system or theme redesign. Animation work. New analytics infrastructure. A scenario-authoring UI (the curated set is a static array, edited by hand). Additional backend capabilities beyond the one `request_log_id` field the trace link needed.
