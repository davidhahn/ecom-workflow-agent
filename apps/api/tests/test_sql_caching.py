"""Integration check that run_sql_query() actually serves a cache hit on a
repeated question, against the real pipeline (real Claude call on the first
request, real Postgres) rather than a mocked one - consistent with how
test_tool_registry.py already exercises the real pipeline."""

from app.query.service import run_sql_query

_QUESTION = "How many products are in the Office category? (cache test, unique phrasing)"


def test_repeated_question_is_served_from_cache_on_second_call():
    first = run_sql_query(_QUESTION)
    second = run_sql_query(_QUESTION)

    assert first.cached is False
    assert second.cached is True
    # cache hit must reproduce the same underlying answer, not just the flag
    assert second.status == first.status
    assert second.rows == first.rows
