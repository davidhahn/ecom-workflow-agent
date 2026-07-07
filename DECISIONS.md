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

---

**Note:** Decision #2 (docker-compose scope) is a direct consequence of the Part 1 scope boundary already recorded in `ARCHITECTURE.md`. Logged here separately because it's concrete enough to defend on its own, but if that upstream scope boundary changes, this entry needs to be revisited rather than treated as independent.
