from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.invoices.router import router as invoices_router
from app.observability.router import router as observability_router
from app.orchestrator.router import router as orchestrator_router
from app.proxy_secret import ProxySecretMiddleware
from app.query.router import router as query_router
from app.rag.router import router as rag_router
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.tickets.router import router as tickets_router

# Production Vercel domain only — no wildcard, no preview-deployment
# support. Defense-in-depth alongside ProxySecretMiddleware (app/proxy_secret.py):
# CORS stops a browser from letting cross-origin JS call this API even if it
# somehow had the shared secret; the secret stops everything CORS can't
# (curl, server-to-server, any non-browser caller).
ALLOWED_ORIGINS = ["https://ecom-workflow-agent-web.vercel.app"]

app = FastAPI(title="Ops Intelligence Agent API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Order matters: FastAPI/Starlette's add_middleware() prepends (inserts at
# position 0), so the *last*-added middleware ends up outermost — it's the
# first to see an incoming request, not the first-added. CORS is added
# last so it's actually outermost: a browser's OPTIONS preflight must be
# answered by CORSMiddleware itself (200/400 based on origin) before
# ProxySecretMiddleware ever sees it, since a preflight never carries
# X-Internal-Proxy-Secret and would otherwise get an unconditional 403
# regardless of origin — silently making the origin allowlist unreachable.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(ProxySecretMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(query_router)
app.include_router(rag_router)
app.include_router(orchestrator_router)
app.include_router(observability_router)
app.include_router(tickets_router)
app.include_router(invoices_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
