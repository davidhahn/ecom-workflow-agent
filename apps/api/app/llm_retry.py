"""One bounded retry for Anthropic calls, using the SDK client directly.

The SDK retries on its own by default (max_retries=2). new_client() turns
that off, so this module is the only thing deciding whether a call
gets retried.
"""

import time
from typing import Any

import anthropic

CALL_TIMEOUT_SECONDS = 30.0
RETRY_DELAY_SECONDS = 2.0

# Network drops, timeouts, rate limits, 5xx - the same failures the SDK
# retries by default. A bad request or an auth failure won't succeed on a
# second try, so those fail right away instead.
RETRYABLE_EXCEPTIONS = (
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class AnthropicCallFailed(Exception):
    """Raised when a call fails for good, first try or retry.

    retry_count is 0 if nothing was retried, 1 if a retry ran and still
    failed. cause is the exception the last attempt raised.
    """

    def __init__(self, retry_count: int, cause: Exception):
        self.retry_count = retry_count
        self.cause = cause
        super().__init__(f"Anthropic call failed, retry_count={retry_count}: {cause}")


def new_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=0, timeout=CALL_TIMEOUT_SECONDS)


def call_with_retry(client: anthropic.Anthropic, **kwargs: Any) -> tuple[Any, int]:
    """Calls client.messages.create, with one retry if the failure looks
    transient. Returns (response, retry_count) on success. Raises
    AnthropicCallFailed if nothing works.
    """
    try:
        return client.messages.create(**kwargs), 0
    except RETRYABLE_EXCEPTIONS:
        time.sleep(RETRY_DELAY_SECONDS)
        try:
            return client.messages.create(**kwargs), 1
        except Exception as second_error:
            raise AnthropicCallFailed(retry_count=1, cause=second_error) from second_error
    except Exception as non_retryable:
        raise AnthropicCallFailed(retry_count=0, cause=non_retryable) from non_retryable
