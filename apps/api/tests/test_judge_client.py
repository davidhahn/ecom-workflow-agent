from unittest.mock import MagicMock, patch

from app.orchestrator.judge_client import judge_answer


def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return MagicMock(content=[block])


def test_judge_answer_parses_valid_json_verdict():
    raw = (
        '{"points_covered": [1, 2], "points_missed": [], '
        '"verdict": "pass", "evidence_summary": "Covers both points."}'
    )
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _text_response(raw)
        result = judge_answer("a question", "an answer", ["point one", "point two"])

    assert result.judge_error is None
    assert result.raw_response == raw
    assert result.verdict.points_covered == [1, 2]
    assert result.verdict.points_missed == []
    assert result.verdict.verdict == "pass"
    assert result.verdict.evidence_summary == "Covers both points."


def test_judge_answer_strips_markdown_code_fence_before_parsing():
    fenced = (
        '```json\n{"points_covered": [1], "points_missed": [2], '
        '"verdict": "fail", "evidence_summary": "Missing point 2."}\n```'
    )
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(fenced)
        result = judge_answer("a question", "an answer", ["point one", "point two"])

    assert result.judge_error is None
    assert result.verdict.points_missed == [2]
    assert result.verdict.verdict == "fail"
    # No retry — fence-stripping is tolerant parsing of the single response.
    assert mock_create.call_count == 1


def test_judge_answer_records_error_on_invalid_json_without_retrying():
    raw = "not valid json at all"
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(raw)
        result = judge_answer("a question", "an answer", ["point one"])

    assert result.verdict is None
    assert result.judge_error is not None
    assert "invalid JSON" in result.judge_error
    assert result.raw_response == raw
    # Must not silently retry just because the format was inconvenient.
    assert mock_create.call_count == 1


def test_judge_answer_records_error_on_json_missing_required_keys():
    raw = '{"verdict": "pass"}'
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _text_response(raw)
        result = judge_answer("a question", "an answer", ["point one"])

    assert result.verdict is None
    assert result.judge_error is not None
    assert "missing required keys" in result.judge_error
    assert result.raw_response == raw
