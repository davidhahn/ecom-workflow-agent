# apps/api

FastAPI backend for the Ops Intelligence Agent. See the root [README](../../README.md) for monorepo-wide setup.

Run locally:

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Database

Schema is managed with SQLAlchemy models (`app/db/models.py`) + Alembic migrations (`alembic/versions/`), not hand-written SQL. With Postgres running (`docker compose up -d` from repo root) and `DATABASE_URL` set in `.env`:

```bash
poetry run alembic upgrade head    # apply migrations
poetry run python -m app.db.seed   # (re-)seed fixture data
```

`app/db/seed.py` is re-runnable — it truncates the six Part 1 tables and reinserts deterministic fixture data each time, so it's safe to run again after a schema change or reset.
