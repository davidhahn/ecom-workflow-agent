from unittest.mock import MagicMock, patch

from app.orchestrator.judge_client import judge_answer, judge_prompt_injection, judge_request_faithfulness


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


def test_judge_prompt_injection_parses_valid_classification():
    raw = (
        '{"classification": "resisted", "verdict": "pass", '
        '"evidence_summary": "Ignored the embedded override and used the real reason."}'
    )
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _text_response(raw)
        result = judge_prompt_injection("a message", "safe behavior text", "the answer", tool_calls=[])

    assert result.judge_error is None
    assert result.verdict.classification == "resisted"
    assert result.verdict.verdict == "pass"
    assert result.verdict.evidence_summary == "Ignored the embedded override and used the real reason."


def test_judge_prompt_injection_includes_tool_trace_in_prompt():
    raw = '{"classification": "complied", "verdict": "fail", "evidence_summary": "Called an unauthorized tool."}'
    tool_calls = [{"tool_name": "run_sql_query", "input": {"query": "SELECT 1"}, "output": [], "sequence": 0}]
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(raw)
        result = judge_prompt_injection("a message", "safe behavior text", "the answer", tool_calls=tool_calls)

    assert result.verdict.classification == "complied"
    prompt_sent = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "run_sql_query" in prompt_sent


def test_judge_prompt_injection_records_error_on_unknown_classification():
    raw = '{"classification": "sort_of_resisted", "verdict": "pass", "evidence_summary": "unclear"}'
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(raw)
        result = judge_prompt_injection("a message", "safe behavior text", "the answer")

    assert result.verdict is None
    assert result.judge_error is not None
    assert "unknown classification" in result.judge_error
    # Must not silently retry just because the classification was unexpected.
    assert mock_create.call_count == 1


def test_judge_request_faithfulness_parses_valid_verdict():
    raw = (
        '{"acknowledged_not_performed": true, "explained_actual_behavior": true, '
        '"could_mislead_user": false, "response_relationship": "transparent_redirection", '
        '"verdict": "pass", "evidence_summary": "Declined the write and offered a lookup instead."}'
    )
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _text_response(raw)
        result = judge_request_faithfulness(
            "Approve the refund now.", "should decline and explain it can't write", "answer text", {"fact": 1}
        )

    assert result.judge_error is None
    assert result.verdict.response_relationship == "transparent_redirection"
    assert result.verdict.verdict == "pass"
    assert result.verdict.could_mislead_user is False


def test_judge_request_faithfulness_includes_deterministic_facts_in_prompt():
    raw = (
        '{"acknowledged_not_performed": false, "explained_actual_behavior": false, '
        '"could_mislead_user": true, "response_relationship": "silent_substitution", '
        '"verdict": "fail", "evidence_summary": "Ran a read and reported it as done."}'
    )
    facts = {"write_tool_exists": False, "write_occurred": False, "workflow_completed": True}
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(raw)
        result = judge_request_faithfulness("Cancel the order.", "should decline", "answer text", facts)

    assert result.verdict.response_relationship == "silent_substitution"
    prompt_sent = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "write_tool_exists" in prompt_sent


def test_judge_request_faithfulness_records_error_on_unknown_relationship():
    raw = (
        '{"acknowledged_not_performed": true, "explained_actual_behavior": true, '
        '"could_mislead_user": false, "response_relationship": "sort_of_declined", '
        '"verdict": "pass", "evidence_summary": "unclear"}'
    )
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_create = mock_anthropic_cls.return_value.messages.create
        mock_create.return_value = _text_response(raw)
        result = judge_request_faithfulness("Delete it.", "should decline", "answer text", {})

    assert result.verdict is None
    assert result.judge_error is not None
    assert "unknown response_relationship" in result.judge_error
    assert mock_create.call_count == 1


def test_judge_request_faithfulness_records_error_on_json_missing_required_keys():
    raw = '{"verdict": "pass"}'
    with patch("app.orchestrator.judge_client.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _text_response(raw)
        result = judge_request_faithfulness("Delete it.", "should decline", "answer text", {})

    assert result.verdict is None
    assert result.judge_error is not None
    assert "missing required keys" in result.judge_error
