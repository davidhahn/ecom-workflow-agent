.PHONY: setup seed test eval

# Brings up Postgres, installs both apps' dependencies, migrates, seeds,
# and ingests the policy corpus. Needs apps/api/.env and apps/web/.env
# already in place (see README's Local Setup section).
setup:
	docker compose up -d
	cd apps/api && poetry install
	cd apps/api && poetry run alembic upgrade head
	$(MAKE) seed
	pnpm install

# Safe to rerun. Truncates and reloads fixture data and the RAG corpus.
seed:
	cd apps/api && poetry run python -m app.db.seed
	cd apps/api && poetry run python -m app.rag.ingest

test:
	cd apps/api && poetry run pytest

# Deterministic subset only: no API key needed, no live model calls.
# Same subset CI runs on every push. For the full suite with live model
# calls, see the Evaluation methodology section of README.md.
eval:
	cd apps/api && poetry run python ../../evals/run.py --subset deterministic
