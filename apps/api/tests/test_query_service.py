"""Tests for run_sql_query()'s retry and failure handling. Same pattern as
test_analyze_service.py's failure-path tests, applied to SQL generation
instead of the analyze loop. Checks a retryable failure that recovers, and
one that doesn't, against the real request_log row each one writes."""

import uuid
from unittest.mock import MagicMock, patch

import anthropic
import httpx
from sqlalchemy import select

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.query.service import run_sql_query

_RUN_ID = uuid.uuid4().hex[:8]


def _fake_anthropic_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _latest_request_log_row(question: str) -> RequestLog:
    with SessionLocal() as session:
        return session.execute(
            select(RequestLog)
            .where(RequestLog.request_type == "sql")
            .where(RequestLog.input == question)
            .order_by(RequestLog.created_at.desc())
        ).scalars().first()


def _valid_tool_use_response():
    block = MagicMock()
    block.type = "tool_use"
    block.input = {"query": "SELECT id FROM products LIMIT 1", "intent": "test query"}
    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[block], stop_reason="tool_use", usage=usage)


def test_clean_call_records_retry_count_zero():
    question = f"a clean SQL question, first attempt works ({_RUN_ID})"
    with patch("app.llm_retry.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _valid_tool_use_response()
        result = run_sql_query(question, bypass_cache=True)

    assert result.status in ("success", "rejected")

    row = _latest_request_log_row(question)
    assert row is not None
    assert row.retry_count == 0


def test_retryable_failure_then_success_records_retry_count_one():
    question = f"a SQL question where the first model call times out ({_RUN_ID})"
    with patch("app.llm_retry.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.side_effect = [
            anthropic.APITimeoutError(request=_fake_anthropic_request()),
            _valid_tool_use_response(),
        ]
        with patch("app.llm_retry.time.sleep") as mock_sleep:
            result = run_sql_query(question, bypass_cache=True)

    assert result.status in ("success", "rejected")
    mock_sleep.assert_called_once()

    row = _latest_request_log_row(question)
    assert row is not None
    assert row.retry_count == 1


def test_call_fails_after_retry_returns_structured_error_not_hang():
    """Trigger a retry, then a second failure, on purpose. run_sql_query()
    should return a structured error instead of hanging, raising, or
    inventing a result. The row it writes should show the retry and the
    failure."""
    question = f"a SQL question where the model call fails twice in a row ({_RUN_ID})"
    with patch("app.llm_retry.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.side_effect = [
            anthropic.APITimeoutError(request=_fake_anthropic_request()),
            anthropic.APIConnectionError(request=_fake_anthropic_request()),
        ]
        with patch("app.llm_retry.time.sleep") as mock_sleep:
            result = run_sql_query(question, bypass_cache=True)

    assert result.status == "error"
    assert result.sql_executed is None
    assert result.row_count == 0
    assert result.rows == []
    mock_sleep.assert_called_once()

    row = _latest_request_log_row(question)
    assert row is not None
    assert row.retry_count == 1
    assert row.output["status"] == "error"
    assert "retry_count=1" in row.output["rejection_reason"]
