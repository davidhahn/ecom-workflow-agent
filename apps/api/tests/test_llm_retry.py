"""Tests for the retry contract in app/llm_retry.py. No real Anthropic
client or DB here, just a mock client and mock responses, checking when
call_with_retry() retries, when it doesn't, and what it returns."""

from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from app.llm_retry import AnthropicCallFailed, call_with_retry


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def test_clean_first_attempt_returns_retry_count_zero():
    client = MagicMock()
    response = MagicMock()
    client.messages.create.return_value = response

    result, retry_count = call_with_retry(client, model="fake")

    assert result is response
    assert retry_count == 0
    assert client.messages.create.call_count == 1


def test_retryable_failure_then_success_returns_retry_count_one():
    client = MagicMock()
    response = MagicMock()
    client.messages.create.side_effect = [
        anthropic.APITimeoutError(request=_fake_request()),
        response,
    ]

    with patch("app.llm_retry.time.sleep") as mock_sleep:
        result, retry_count = call_with_retry(client, model="fake")

    assert result is response
    assert retry_count == 1
    assert client.messages.create.call_count == 2
    mock_sleep.assert_called_once()


def test_two_retryable_failures_raises_with_retry_count_one():
    client = MagicMock()
    client.messages.create.side_effect = [
        anthropic.APITimeoutError(request=_fake_request()),
        anthropic.APIConnectionError(request=_fake_request()),
    ]

    with patch("app.llm_retry.time.sleep"):
        with pytest.raises(AnthropicCallFailed) as exc_info:
            call_with_retry(client, model="fake")

    assert exc_info.value.retry_count == 1
    assert client.messages.create.call_count == 2


def test_non_retryable_failure_raises_immediately_without_retry():
    client = MagicMock()
    client.messages.create.side_effect = ValueError("not a transient failure")

    with patch("app.llm_retry.time.sleep") as mock_sleep:
        with pytest.raises(AnthropicCallFailed) as exc_info:
            call_with_retry(client, model="fake")

    assert exc_info.value.retry_count == 0
    assert client.messages.create.call_count == 1
    mock_sleep.assert_not_called()
