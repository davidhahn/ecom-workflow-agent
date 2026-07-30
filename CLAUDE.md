# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Project
Enterprise Operations Intelligence Agent — an eCommerce ops assistant. Part 1 scope targets one working SQL path (refund-rate analysis) and one working RAG path (refund policy lookup) over eCommerce operations data, proven end-to-end before agents, security controls, or observability tooling are added. See `ARCHITECTURE.md` for the full decision record.

## Stack
Monorepo: `apps/web` (Next.js 16, TypeScript, Tailwind), `apps/api` (Python 3.14, FastAPI, uvicorn, Poetry), `packages/shared` (generated-only TS types via openapi-typescript — never hand-written). Postgres + pgvector is committed and running via `docker-compose.yml`; schema is SQLAlchemy models + Alembic migrations under `apps/api/app/db/`, seeded via the re-runnable `apps/api/app/db/seed.py`. Full stack table and rationale for each choice live in `ARCHITECTURE.md` — don't duplicate it here, it will drift.

## Architecture boundaries
Orchestration seam is "LLM proposes, Python enforces": Claude extracts intent via structured tool-calling, a Python state machine owns all execution authorization, the LLM never executes directly. Two separate gates — a deterministic **structural gate** (SQL verb/table/column permission, refund threshold checks, approval routing) and a probabilistic **groundedness check** (verifies RAG-sourced claims against the retrieved passage). Neither gate substitutes for the other. See `ARCHITECTURE.md` for the full reasoning and open questions (PII column-scoping is explicitly undecided).

## Coding standards
- **Traceability Rule**: Never accept a change I can't read, manually trace, and explain out loud. If the diff is too large to manually trace a single example through, the task was too large — split it.
- **Fail Loudly**: When interacting with mock or real enterprise systems, explicit failures are features. Never catch an exception and return a silent empty state or generic fallback unless explicitly commanded.
- **Strict UI States**: All frontend components must account for streaming states, loading states, and partial JSON chunks.

## What not to touch
- **`ARCHITECTURE.md`** — I own this file's content. Don't edit it as a side effect of other work; if a change seems to require it, ask first.
- **`EVALS.md`** — mine to fill in. Leave it alone unless I ask you to write to it.
- Once an eval harness exists: eval cases and their expected outputs/scoring rubrics will be off-limits the same way — fix the code or the prompt, never edit a test's expected answer to force a passing grade.
- These two files still go stale — you don't get to fix that by editing them, but you do get to notice. Whenever a task has you reading or changing code that a specific claim in `ARCHITECTURE.md` or `EVALS.md` depends on (a stack-table row, a case count, a "known limitation," an "in progress" status), check whether that claim still holds and say so if it doesn't — don't wait for a dedicated audit request. This isn't a standing background scan of the whole repo; it's triggered by what you're already touching.

## Running tests
- No eval scoring harness yet (Part 1 has eval case drafts in `evals/cases.json` but no runner). A small `pytest` suite exists at `apps/api/tests/` (currently just the tool registry contract tests — run with `poetry run pytest` from `apps/api`); extend it as more of the backend gets test coverage, rather than treating "no harness" as still true. For anything not yet covered, verify manually: `poetry run alembic upgrade head` / `poetry run python -m app.db.seed` for schema changes, `pnpm --filter web run build` for frontend changes, direct `curl` against the running FastAPI app for endpoint changes.

## Secrets
- **Zero-Exposure Rule**: API keys, tokens, and DB strings live exclusively in `.env` (gitignored, one per app — `apps/web/.env`, `apps/api/.env`). `.env.example` files are tracked and must contain placeholders only, never a real credential. You must never hardcode a literal credential string in the codebase. If you write `sk-ant-`, `sk-proj-`, or `sk-svc-` followed by real-looking characters anywhere outside a gitignored `.env` file, you have failed the most critical check.

## Decisions
- When making a non-trivial architectural choice (e.g. how the agent decides between the SQL refund-rate path and the RAG policy-lookup path, or how we format the JSON trace logs), the reasoning, tradeoffs, and failure modes must be explicitly recorded in `DECISIONS.md`. Keep the markdown formatting extremely clean so the raw text can be seamlessly ported over into project tracking workspaces like Notion later.
