"""Tests for data_analyst.gather_evidence()/investigate_gather_evidence().

test_one_sql_failure_does_not_prevent_other_signals_from_completing is the
one worth calling out: it's not an incidental check, it's the specific
property this module's per-signal error handling exists to guarantee (see
data_analyst.py's module docstring). Built against a hand-constructed plan
rather than a live Planner call, so which signal fails is deterministic
rather than dependent on how Claude happened to phrase this run's plan."""

from unittest.mock import patch

from app.orchestrator.data_analyst import gather_evidence, investigate_gather_evidence
from app.orchestrator.investigation_planner import InvestigationPlan, InvestigationSignal
from app.query.service import run_sql_query as real_run_sql_query

CANONICAL_QUESTION = "Why did revenue drop last week?"


def test_investigate_gather_evidence_all_signals_succeed_against_real_seeded_data():
    bundle = investigate_gather_evidence(CANONICAL_QUESTION)

    assert len(bundle.evidence) == len(bundle.plan.signals)
    for entry in bundle.evidence:
        assert entry.status == "success", f"{entry.name} ({entry.method}) came back {entry.status}: {entry.detail}"
        if entry.method == "sql":
            assert entry.sql_result is not None
            assert entry.sql_result.status == "success"
        else:
            assert entry.rag_result is not None
            assert len(entry.rag_result.chunks) > 0


def test_one_sql_failure_does_not_prevent_other_signals_from_completing():
    failing_intent = "Compute total revenue for the last 7 days vs. the prior 7 days from orders."
    plan = InvestigationPlan(
        signals=[
            InvestigationSignal(name="revenue", method="sql", intent=failing_intent),
            InvestigationSignal(
                name="traffic_conversion",
                method="sql",
                intent=(
                    "Compare total sessions and average conversion_rate for the last 7 days "
                    "vs. the prior 7 days from web_analytics."
                ),
            ),
            InvestigationSignal(
                name="refunds",
                method="sql",
                intent="Compute refund count and total refund amount for the last 7 days vs. the prior 7 days.",
            ),
            InvestigationSignal(
                name="campaign_context",
                method="rag",
                intent="Search company notes for a marketing campaign that recently ended.",
            ),
        ]
    )

    def fake_run_sql_query(question: str):
        if question == failing_intent:
            raise RuntimeError("simulated SQL backend outage")
        return real_run_sql_query(question)

    with patch("app.orchestrator.data_analyst.run_sql_query", side_effect=fake_run_sql_query):
        evidence = gather_evidence(plan)

    assert len(evidence) == 4

    revenue_entry, traffic_entry, refund_entry, campaign_entry = evidence

    assert revenue_entry.status == "failed"
    assert revenue_entry.sql_result is None
    assert "simulated SQL backend outage" in revenue_entry.detail

    # The property under test: the other three still ran for real and
    # completed normally, unaffected by the one signal that blew up.
    assert traffic_entry.status == "success"
    assert refund_entry.status == "success"
    assert campaign_entry.status == "success"


def test_rag_signal_with_no_matching_chunks_is_marked_empty_not_failed():
    plan = InvestigationPlan(
        signals=[
            InvestigationSignal(name="no_match", method="rag", intent="irrelevant"),
        ]
    )

    with patch("app.orchestrator.data_analyst.query_rag") as mock_query_rag:
        mock_query_rag.return_value.chunks = []
        evidence = gather_evidence(plan)

    assert len(evidence) == 1
    assert evidence[0].status == "empty"
    assert evidence[0].detail is not None
