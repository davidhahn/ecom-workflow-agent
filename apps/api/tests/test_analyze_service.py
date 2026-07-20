"""Tests for analyze_service.analyze()'s tool-loop-exhaustion handling
(Fix 2: MAX_TOOL_ITERATIONS reached while Claude is still requesting tools
must return an explicit incomplete state, not an empty answer that trivially
passes check_groundedness) and for the tool-call tracing captured into
request_log.tool_calls during that same loop.

analyze() doesn't return its own request_log row, so tests that need to
inspect tool_calls query request_log directly by (request_type, input) —
same pattern as test_invoices.py querying request_log for confirm-attempt
detail. Questions are given a unique per-run suffix so a rerun's row can't
collide with (or be shadowed by) a previous run's row for the same input,
and so analyze()'s in-memory question cache can't turn a rerun into a cache
hit that skips the tool loop entirely."""

import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.orchestrator.analyze_service import MAX_TOOL_ITERATIONS, analyze

_RUN_ID = uuid.uuid4().hex[:8]


def _latest_request_log_row(question: str) -> RequestLog:
    with SessionLocal() as session:
        return session.execute(
            select(RequestLog)
            .where(RequestLog.request_type == "analyze")
            .where(RequestLog.input == question)
            .order_by(RequestLog.created_at.desc())
        ).scalars().first()


def _tool_use_block(name: str, tool_input: dict, block_id: str):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = tool_input
    block.id = block_id
    return block


def _fake_tool_use_response():
    """A Claude response that always keeps requesting a tool call, never
    reaching a final text answer - simulates the loop never hitting its
    natural `break`."""
    block = _tool_use_block(
        "search_policy", {"query": "loop should exhaust before this is ever cited"}, "fake_tool_use_id"
    )
    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[block], stop_reason="tool_use", usage=usage)


def test_tool_loop_exhaustion_returns_incomplete_not_empty_grounded_answer():
    question = f"a question the assistant never stops trying to tool-call for ({_RUN_ID})"
    with patch("app.orchestrator.analyze_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _fake_tool_use_response()
        result = analyze(question)

    assert result.incomplete is True
    assert result.answer != ""
    # The old bug: an empty answer trivially "passes" groundedness. Confirm
    # this path is marked ungrounded/unevaluated instead of a misleading
    # grounded=True.
    assert result.grounded is False
    assert result.ungrounded_claims == []

    # tool_calls must still be a valid, readable array up to the point of
    # exhaustion, not a broken/partial structure — one entry per iteration,
    # since the fake response requests exactly one tool per turn and the
    # loop runs MAX_TOOL_ITERATIONS times before giving up.
    row = _latest_request_log_row(question)
    assert row is not None
    assert row.tool_calls is not None
    assert len(row.tool_calls) == MAX_TOOL_ITERATIONS
    assert [c["sequence"] for c in row.tool_calls] == list(range(MAX_TOOL_ITERATIONS))
    for call in row.tool_calls:
        assert call["tool_name"] == "search_policy"
        assert isinstance(call["latency_ms"], int)
        assert call["latency_ms"] >= 0
        assert call["input"] == {"query": "loop should exhaust before this is ever cited"}
        assert isinstance(call["output"], list)


def _dual_tool_call_response():
    sql_block = _tool_use_block(
        "run_sql_query",
        {"query": "SELECT id, category FROM products LIMIT 3", "intent": "tool trace test"},
        "tool_sql",
    )
    rag_block = _tool_use_block(
        "search_policy", {"query": "how long do I have to return a defective item?"}, "tool_rag"
    )
    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[sql_block, rag_block], stop_reason="tool_use", usage=usage)


def _final_text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[block], stop_reason="end_turn", usage=usage)


def test_tool_calls_trace_captures_sql_and_rag_calls_in_order():
    question = f"trace test needing both data and policy context ({_RUN_ID})"
    responses = [
        _dual_tool_call_response(),
        _final_text_response("Per rule 4, defective items can be returned; see the data above."),
    ]
    with patch("app.orchestrator.analyze_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.side_effect = responses
        result = analyze(question)

    assert result.sql_used is True
    assert result.rag_used is True

    row = _latest_request_log_row(question)
    assert row is not None
    assert row.tool_calls is not None
    assert len(row.tool_calls) == 2

    sql_call, rag_call = row.tool_calls
    assert [sql_call["sequence"], rag_call["sequence"]] == [0, 1]
    assert sql_call["tool_name"] == "run_sql_query"
    assert rag_call["tool_name"] == "search_policy"
    for call in row.tool_calls:
        assert isinstance(call["latency_ms"], int)
        assert call["latency_ms"] >= 0
        assert call["input"]
        assert call["output"] is not None
