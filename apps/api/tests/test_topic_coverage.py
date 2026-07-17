"""Tests for the structural topic-coverage check (Fix for the live gap:
check_groundedness() can pass (citation accurate) while the answer's actual
data-driven claim is fabricated from a table with no bearing on the
question, e.g. inferring shipment delay from orders.status)."""

from app.orchestrator.analyze_service import analyze
from app.orchestrator.topic_coverage import check_topic_coverage


def test_check_topic_coverage_flags_uncovered_topic_with_no_shipments_sql():
    answer = "Based on order status, 3 orders could be at risk of delay."
    assert check_topic_coverage(answer, sql_used=True, generated_sql=["SELECT status FROM orders"]) is True


def test_check_topic_coverage_does_not_flag_when_sql_actually_queried_shipments():
    answer = "3 shipments are currently delayed."
    assert (
        check_topic_coverage(
            answer, sql_used=True, generated_sql=["SELECT status FROM shipments WHERE status = 'delayed'"]
        )
        is False
    )


def test_check_topic_coverage_does_not_flag_unrelated_answer():
    answer = "The refund rate for Electronics is 12%."
    assert check_topic_coverage(answer, sql_used=True, generated_sql=["SELECT * FROM refunds"]) is False


def test_check_topic_coverage_flags_even_with_no_sql_at_all():
    answer = "Tracking shows your carrier is en route."
    assert check_topic_coverage(answer, sql_used=False, generated_sql=[]) is True


def test_live_shipment_delay_question_triggers_topic_coverage_warning():
    """Reproduces the exact live case: a question about shipment delays,
    with only run_sql_query/search_policy available (get_shipment_status is
    not wired into analyze_service.py yet). The answer must either say it
    doesn't have shipment data, or - if it still speculates - come back
    flagged."""
    result = analyze("are any shipments delayed right now? (topic coverage test, unique phrasing)")

    no_data_claim = "shipment" in result.answer.lower() and (
        "don't have" in result.answer.lower()
        or "do not have" in result.answer.lower()
        or "not available" in result.answer.lower()
        or "no access" in result.answer.lower()
        or "cannot" in result.answer.lower()
        or "can't" in result.answer.lower()
    )
    assert no_data_claim or result.topic_coverage_warning is True, (
        f"answer neither honestly declined nor got flagged: {result.answer!r}"
    )


def test_live_ordinary_refund_question_does_not_trigger_topic_coverage_warning():
    """Contrast/false-positive check: a question genuinely answerable from
    orders/refunds data, with no delay/shipment language, must not trip the
    warning."""
    result = analyze(
        "What is the refund rate for the Electronics category? (topic coverage contrast test)"
    )
    assert result.topic_coverage_warning is False
