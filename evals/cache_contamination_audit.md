# Cache Contamination Audit — 2026-08-06

Question: were the "8 clean runs" real, independent model calls, or cache hits reusing the first run's answer?

## Answer: no contamination.

**Why it can't happen:** the app cache is a plain dictionary in memory that lives inside one process. `evals/run.py` starts a new process every time it runs, so the cache is empty at the start of every run.

**What the data shows:** checked `request_log` (2,235 rows, July 13 – Aug 5).

- The real eval questions (sql, rag, mixed) never show `cached: true` when repeated. Every repeat got a fresh model call, with output tokens and latency changing each time (e.g. 187–207 tokens, 3.1–3.9s for the same question asked 10+ times).
- `rag` has never been served from cache.
- The `cached: true` rows that do exist for `sql` trace back to the suite's intentional cache test.
