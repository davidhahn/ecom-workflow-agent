"""Shared-secret check between the Next.js Edge Middleware proxy
(apps/web/middleware.ts) and this backend. The deployed FastAPI URL has no
other authentication in front of it, so this is what actually stands
between that URL and anyone who finds it — implemented as blanket ASGI
middleware (checked on every request) rather than a per-route dependency
like app/permissions.py's X-Demo-Role check, specifically so a new route
can't forget to add it. CORS (configured in app/main.py) is a separate,
independent layer: it's enforced by browsers and does nothing against a
direct server-to-server or curl request, which is exactly the gap this
header check closes. Neither substitutes for the other.

INTERNAL_PROXY_SECRET is read once at import time via os.environ[...] (not
.get() with a default) so a deploy that forgot to set it fails loudly at
startup instead of silently serving requests as if they were open — the
same "required, not optional" pattern OPS_AGENT_DB_PASSWORD already uses in
app/query/db_readonly.py.
"""

import os

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

INTERNAL_PROXY_SECRET = os.environ["INTERNAL_PROXY_SECRET"]

HEADER_NAME = "X-Internal-Proxy-Secret"

# Render's own health check hits this path directly (see render.yaml's
# healthCheckPath) and never carries the header — the one exemption.
EXEMPT_PATHS = {"/health"}


class ProxySecretMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        provided = request.headers.get(HEADER_NAME)
        if provided != INTERNAL_PROXY_SECRET:
            return JSONResponse(
                {
                    "error": "forbidden",
                    "message": f"Missing or invalid {HEADER_NAME} header.",
                },
                status_code=403,
            )

        return await call_next(request)
