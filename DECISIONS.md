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

---

**Note:** Decision #2 (docker-compose scope) is a direct consequence of the Part 1 scope boundary already recorded in `ARCHITECTURE.md`. Logged here separately because it's concrete enough to defend on its own, but if that upstream scope boundary changes, this entry needs to be revisited rather than treated as independent.
