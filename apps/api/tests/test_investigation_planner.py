"""Tests for investigation_planner.plan_investigation() — a real Claude call
(no mocking), same as test_tickets.py/test_refund_evaluator.py's approach to
LLM-driven extraction: this is testing whether the system prompt actually
elicits the intended plan shape from a real model, which a mocked response
can't verify.

Signal names are Claude's own free choice, not a fixed vocabulary — assertions
match on method + intent keywords, not exact name strings, so the test isn't
coupled to exactly how Claude happens to phrase a signal name this run."""

from app.orchestrator.investigation_planner import InvestigationSignal, plan_investigation

CANONICAL_QUESTION = "Why did revenue drop last week?"


def _find(signals: list[InvestigationSignal], method: str, keyword: str) -> InvestigationSignal | None:
    keyword = keyword.lower()
    return next(
        (
            s
            for s in signals
            if s.method == method and (keyword in s.name.lower() or keyword in s.intent.lower())
        ),
        None,
    )


def test_canonical_revenue_drop_question_produces_a_plan_with_all_four_signals():
    plan = plan_investigation(CANONICAL_QUESTION)

    assert len(plan.signals) >= 4
    for signal in plan.signals:
        assert signal.method in ("sql", "rag")
        assert signal.name
        assert signal.intent

    revenue_signal = _find(plan.signals, "sql", "revenue")
    assert revenue_signal is not None, f"no sql revenue signal in {plan.signals}"

    traffic_signal = _find(plan.signals, "sql", "session") or _find(plan.signals, "sql", "conversion")
    assert traffic_signal is not None, f"no sql traffic/conversion signal in {plan.signals}"

    refund_signal = _find(plan.signals, "sql", "refund")
    assert refund_signal is not None, f"no sql refund signal in {plan.signals}"

    campaign_signal = _find(plan.signals, "rag", "campaign")
    assert campaign_signal is not None, f"no rag campaign-context signal in {plan.signals}"
