# Product Spec: Enterprise Operations Intelligence Agent

## Problem

Ops and support analysts answer the same two kinds of questions constantly: "what does the data say" (refund rates, order trends, product-level patterns) and "what does policy say" (return windows, exclusions, approval thresholds). Today that means either writing SQL against the operations database directly, or hunting through policy markdown docs by hand — both slow, both require knowledge most analysts on the team don't have (SQL) or don't have memorized (the exact wording of every policy rule), and both are easy to get subtly wrong in a way that isn't obvious until a customer disputes the answer.

This project builds a natural-language interface to both — one agent an analyst can ask a question in plain English, and trust the answer is either backed by a real query against real data, backed by an actual policy citation, or both.

## Users

Primary: **ops and support analysts** — the people who field refund disputes, run ad hoc reporting for their lead, and decide (or recommend) whether a specific refund request should be approved. They are not SQL-literate and should never need to be. They need answers fast, and they need to be able to trust or verify those answers without independently re-deriving them.

Secondary: whoever reviews this agent's own behavior — spot-checking whether its answers were actually grounded, whether it's rejecting the SQL it should reject. Part 1 supports this only as a byproduct (every request is logged), not as a dedicated workflow.

## Goals (Part 1)

Part 1 exists to prove two things work end-to-end, on real data, before anything else gets built on top of them:

1. **A natural-language question about ops data gets answered from a real, safe, read-only SQL query** — not a fabricated number, not an unrestricted query against the database.
2. **A natural-language question about refund policy gets answered from the actual policy document** — not the model's general knowledge or a plausible-sounding guess, and any claim citing a specific rule can be checked against what was actually retrieved.

A third surface, **refund request evaluation**, was built alongside these to give the RAG path's policy rules a concrete, deterministic consumer: given a free-text refund request, resolve it against real order data and return a decision (approve / deny / needs manager approval / flag for review / can't process) with the specific rule that drove it — without ever guessing a value it isn't confident about.

## Non-Goals (Part 1)

Deliberately out of scope for this phase — not because they don't matter, but because proving the two core paths work has to come first:

- **Executing** a refund decision (writing to the `refunds` table). Part 1 evaluates and recommends only.
- Multi-agent decomposition, model routing, or any orchestration beyond a single tool-calling loop as a user-facing feature — a Planner → Data Analyst pipeline already exists (`app/orchestrator/investigation_planner.py`, `data_analyst.py`) but isn't wired to an endpoint yet (see `DECISIONS.md` #26).
- No dedicated prompt-injection defense feature exists — though an 8-case `prompt_injection` eval category is actively run against the system, with at least one documented finding (see `DECISIONS.md` #9, the fabricated-rule-number case). Auth/RBAC and row-level data isolation remain out of scope (the structural gate restricts *what* can be queried — tables, columns, verbs — not *whose* data a given caller can see).
- Full PII column-scoping — only `customers.email` is currently hardcoded out of reach. See `ARCHITECTURE.md`'s open questions.
- A dedicated review/monitoring workflow for analysts auditing the agent's own answers — request logging exists, but nothing is built on top of it yet.

Full technical rationale for these boundaries lives in `ARCHITECTURE.md`; this doc states the product boundary, not the engineering reasoning behind it.

## Use Cases

**1. Ask an ops data question.**
_"What's our refund rate for Electronics this quarter?"_ → the agent decides whether it needs live data, policy text, or both, runs whatever's needed, and answers in plain language with the query's result reflected accurately.

**2. Ask a policy question.**
_"Can a customer return a clearance item?"_ → the agent answers from the actual refund policy document and states which rule the answer rests on, so the analyst (or the customer) can go check it themselves.

**3. Ask a question that needs both.**
_"Are we seeing more refund requests than our repeat-refund policy should be catching?"_ → the agent pulls real numbers and checks them against the actual policy rule in the same answer, rather than answering only the data half or only the policy half.

**4. Evaluate a specific refund request.**
An analyst pastes in a customer's free-text refund request → the agent resolves it against the real order/customer record and returns a decision, the specific policy rule that decision rests on, and its reasoning — or honestly says it can't process the request rather than guessing.

## Functional Requirements

- A single natural-language endpoint that can use a SQL tool, a policy-retrieval tool, both, or neither, depending on the question.
- Every SQL query the agent runs must be a read-only `SELECT` against an explicit table/column allowlist, with no path for the agent to execute a write, regardless of how the question is phrased.
- Every answer that cites a specific policy rule must be checked against what was actually retrieved for that request, and the answer must say so if a cited rule wasn't actually retrieved.
- Refund evaluation must resolve against real order/customer records — never invent an order, a customer, or a refund amount — and must refuse to guess (rather than pick the most likely option) when the request text doesn't clearly map to one of the known reason codes.
- Every request to any of the above must be logged (input, output, timing, cost) whether it succeeds, gets rejected, or errors.

## Success Criteria

- A representative set of ops-data questions gets answered with real, correct query results (validated by `evals/cases.json`'s `sql` and `mixed` cases).
- A representative set of policy questions retrieves the actual governing rule in its top results (validated by the `rag` cases).
- Adversarial or unsafe SQL requests (write attempts, blocked columns, disallowed tables) are rejected before execution, every time — this is a 100%-or-it's-broken bar, not a target to trend toward.
- The groundedness check correctly flags a citation to a rule that wasn't actually retrieved, and correctly passes a citation that was (validated by the `groundedness` cases).
- Refund evaluation reaches the correct decision, for the correct policy reason, on known real order rows — and correctly declines to process ambiguous or unresolvable requests instead of guessing (validated by the `refund_evaluator` cases).

## What's Next

Later phases — multi-agent orchestration, security hardening, observability tooling beyond request logging — are intentionally undesigned until the above is proven. See `ARCHITECTURE.md` for the scope boundary and open questions that later phases will need to resolve.
