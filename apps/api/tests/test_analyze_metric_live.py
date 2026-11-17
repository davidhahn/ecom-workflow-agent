"""Opt-in semantic regression through Ask's real model/tool path.

RUN_LIVE_METRIC_TEST=1 poetry run pytest tests/test_analyze_metric_live.py -q
Requires the seeded Postgres database and configured Anthropic access.
"""
import os

import pytest
from sqlalchemy import select, text

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.orchestrator.analyze_service import analyze
from app.query.db_readonly import readonly_engine


@pytest.mark.skipif(os.environ.get("RUN_LIVE_METRIC_TEST") != "1", reason="opt-in live model and database test")
def test_ask_home_refund_rate_matches_independent_unit_calculation():
    # EXISTS counts each sold line once, even if it has multiple refund records.
    with readonly_engine.connect() as conn:
        expected = conn.execute(text("""
            SELECT SUM(CASE WHEN EXISTS (
                SELECT r.id FROM refunds r
                WHERE r.order_item_id = oi.id AND r.status = 'approved'
            ) THEN oi.quantity ELSE 0 END)::numeric
                / NULLIF(SUM(oi.quantity), 0)
            FROM order_items oi JOIN products p ON p.id = oi.product_id
            WHERE p.category = 'Home'
        """)).scalar_one()

    result = analyze(
        "What is the refund rate for Home category products? "
        "Return the SQL result as a single decimal ratio column named refund_rate, not a percentage.",
        bypass_cache=True,
    )
    assert not result.incomplete
    assert result.sql_used
    with SessionLocal() as session:
        log = session.execute(select(RequestLog).where(RequestLog.id == result.request_log_id)).scalar_one()
        calls = [call for call in log.tool_calls if call["tool_name"] == "run_sql_query"]
    assert calls
    output = calls[-1]["output"]
    assert output["status"] == "success"
    assert len(output["rows"]) == 1
    assert float(output["rows"][0]["refund_rate"]) == pytest.approx(float(expected), abs=0.0001)
