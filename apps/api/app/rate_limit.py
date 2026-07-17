"""Shared slowapi Limiter instance + custom 429 handler.

Defined in its own module (not main.py) so router modules can import
`limiter` for the `@limiter.limit(...)` decorator without a circular import
(main.py imports the routers; the routers need the limiter).

IP-based (get_remote_address) since there's no auth to key rate limits on
yet — see PRODUCT_SPEC.md's non-goals.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# headers_enabled=True: makes slowapi inject X-RateLimit-Limit/Remaining/Reset
# into every response on a decorated route (success or 429), not just 429s.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Same Retry-After / X-RateLimit-* header computation as slowapi's own
    default handler (reused directly, not reimplemented), with a JSON body
    shaped for the frontend to render without parsing headers itself."""
    default_response = _rate_limit_exceeded_handler(request, exc)
    retry_after = default_response.headers.get("Retry-After")
    body = {
        "error": "rate_limited",
        "retry_after_seconds": int(retry_after) if retry_after is not None else None,
        "message": (
            f"Rate limit exceeded. Try again in {retry_after} seconds."
            if retry_after is not None
            else "Rate limit exceeded."
        ),
    }
    # Only carry over the rate-limit-specific headers, not the whole header
    # set: default_response's Content-Length was computed for *its* body,
    # not ours, and copying it verbatim causes a framing mismatch (the
    # response then gets truncated by the client) since our JSON body is a
    # different length.
    rate_limit_headers = {
        k: v
        for k, v in default_response.headers.items()
        if k.lower() in ("retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")
    }
    return JSONResponse(body, status_code=429, headers=rate_limit_headers)
