"""Tests for analyze_service.analyze()'s tool-loop-exhaustion handling
(Fix 2: MAX_TOOL_ITERATIONS reached while Claude is still requesting tools
must return an explicit incomplete state, not an empty answer that trivially
passes check_groundedness)."""

from unittest.mock import MagicMock, patch

from app.orchestrator.analyze_service import analyze


def _fake_tool_use_response():
    """A Claude response that always keeps requesting a tool call, never
    reaching a final text answer - simulates the loop never hitting its
    natural `break`."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = "search_policy"
    block.input = {"query": "loop should exhaust before this is ever cited"}
    block.id = "fake_tool_use_id"

    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[block], stop_reason="tool_use", usage=usage)


def test_tool_loop_exhaustion_returns_incomplete_not_empty_grounded_answer():
    with patch("app.orchestrator.analyze_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _fake_tool_use_response()
        result = analyze("a question the assistant never stops trying to tool-call for")

    assert result.incomplete is True
    assert result.answer != ""
    # The old bug: an empty answer trivially "passes" groundedness. Confirm
    # this path is marked ungrounded/unevaluated instead of a misleading
    # grounded=True.
    assert result.grounded is False
    assert result.ungrounded_claims == []
