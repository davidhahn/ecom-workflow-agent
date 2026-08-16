"""Fixed-input tests for the SQL safety machinery (app/query/validation.py).
Each test feeds a known SQL string or cost number straight into
validate_ast()/check_cost(). No model call, no live database. See
DECISIONS.md #47: the sql eval category still needs a model to generate
the SQL it scores, so this file covers the guardrails on their own."""

import pytest

from app.query.validation import SqlRejected, check_cost, validate_ast


def test_write_query_is_rejected():
    with pytest.raises(SqlRejected):
        validate_ast("DELETE FROM refunds WHERE id = 'x'")


def test_blocked_column_is_rejected():
    with pytest.raises(SqlRejected):
        validate_ast("SELECT email FROM customers")


def test_disallowed_table_is_rejected():
    # shipments is a real table, just not in ALLOWED_TABLES. The general
    # SQL path has no access to shipment data (see the shipment-tracking
    # line in analyze_service.SYSTEM_PROMPT).
    with pytest.raises(SqlRejected):
        validate_ast("SELECT id, status FROM shipments")


def test_valid_read_only_sql_is_accepted():
    statement = validate_ast("SELECT id, status FROM refunds WHERE status = 'approved'")
    assert statement is not None


def test_cost_gate_allows_at_or_below_threshold():
    check_cost(10_000.0)


def test_cost_gate_rejects_above_threshold():
    with pytest.raises(SqlRejected):
        check_cost(10_000.01)
