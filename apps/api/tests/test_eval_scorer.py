"""Proves the sql_semantic scorer catches a wrong answer, not just that it
lets correct ones through - a scorer only ever seen passing isn't verified.

evals/run.py isn't a package, so it's imported by file path."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evals"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("evals_run", REPO_ROOT / "evals" / "run.py")
evals_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evals_run)

from app.query.claude_client import ProposedQuery  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402


CASE_ID = "sql-semantic-01-home-refund-rate-denominator"

# Same mistake as the real, confirmed bug in sql-01/sql-semantic-01: counts
# rows instead of unit quantity, and includes non-approved refunds.
WRONG_SQL = """SELECT
  COUNT(DISTINCT r.id) AS total_refunds,
  COUNT(DISTINCT oi.id) AS total_order_items,
  ROUND(COUNT(DISTINCT r.id)::numeric / COUNT(DISTINCT oi.id), 4) AS refund_rate
FROM order_items oi
JOIN products p ON p.id = oi.product_id
LEFT JOIN refunds r ON r.order_item_id = oi.id
WHERE p.category = 'Home'"""


@pytest.fixture
def case() -> dict:
    return next(c for c in evals_run.load_cases() if c["id"] == CASE_ID)


def test_wrong_denominator_query_runs_clean_but_fails_the_scorer(case):
    """Runs WRONG_SQL through the real /query/sql pipeline, Claude skipped
    so the wrong query is fixed, not left to chance."""
    from fastapi.testclient import TestClient

    from app.main import app as fastapi_app

    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})
    expected = case["expected"]

    with patch("app.query.service.propose_sql") as mock_propose:
        mock_propose.return_value = ProposedQuery(query=WRONG_SQL, intent="deliberately wrong denominator")
        response = client.post("/query/sql", json={"question": case["input"]})

    body = response.json()

    # Runs clean - it's a valid, safe query. Only the answer is wrong.
    assert body["status"] == "success"
    assert evals_run._check_tables_joined(body["sql_executed"].lower(), expected["tables_joined"]) == []

    reasons = evals_run._check_expected_result(expected["expected_result"], body["rows"])

    assert reasons, "scorer passed a query that computes the wrong refund rate"
    assert "expected result: 0.0833 ± 0.01" in reasons
    assert "actual result:   0.1304" in reasons
    # The hand-written note is the last line, shown as-is, never guessed.
    assert reasons[-1] == expected["expected_result"]["review_note"]


def test_scorer_rejects_a_fixture_of_the_known_wrong_rows():
    """Same check, no DB or app needed - just the rows the wrong query
    above actually returns."""
    expected_result = {
        "type": "scalar",
        "value": 0.0833,
        "comparison": "absolute_tolerance",
        "tolerance": 0.01,
    }
    known_wrong_rows = [{"total_refunds": 3, "total_order_items": 23, "refund_rate": "0.1304"}]

    reasons = evals_run._check_expected_result(expected_result, known_wrong_rows)

    assert reasons == ["expected result: 0.0833 ± 0.01", "actual result:   0.1304"]
