"""Tests for the shared slowapi wiring (app/rate_limit.py): the mechanism
itself, not each business endpoint's specific per-route number (those are
visible directly in the router files - no need to burn real Claude calls
just to prove e.g. /query/analyze's 10/hour is wired up).

Uses a throwaway FastAPI app with one dummy route decorated with the real
`limiter`/`rate_limit_exceeded_handler`, so this is a true exercise of the
production wiring, not a reimplementation of it.
"""

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.rate_limit import limiter, rate_limit_exceeded_handler


def _make_test_app() -> FastAPI:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/dummy")
    @limiter.limit("2/minute")
    def dummy(request: Request, response: Response) -> dict:
        return {"ok": True}

    return app


def test_successful_responses_carry_decrementing_remaining_header():
    client = TestClient(_make_test_app())

    first = client.get("/dummy")
    second = client.get("/dummy")

    assert first.status_code == 200
    assert second.status_code == 200
    assert int(first.headers["X-RateLimit-Remaining"]) > int(second.headers["X-RateLimit-Remaining"])


def test_exceeding_the_limit_returns_429_with_custom_body_and_retry_after():
    client = TestClient(_make_test_app())

    client.get("/dummy")
    client.get("/dummy")
    third = client.get("/dummy")  # limit is 2/minute - this one should be rejected

    assert third.status_code == 429
    assert "Retry-After" in third.headers

    body = third.json()
    assert body["error"] == "rate_limited"
    assert isinstance(body["retry_after_seconds"], int)
    assert body["retry_after_seconds"] > 0
    assert "try again" in body["message"].lower() or "rate limit" in body["message"].lower()
