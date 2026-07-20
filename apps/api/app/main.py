from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.invoices.router import router as invoices_router
from app.observability.router import router as observability_router
from app.orchestrator.router import router as orchestrator_router
from app.query.router import router as query_router
from app.rag.router import router as rag_router
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.tickets.router import router as tickets_router

app = FastAPI(title="Ops Intelligence Agent API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.include_router(query_router)
app.include_router(rag_router)
app.include_router(orchestrator_router)
app.include_router(observability_router)
app.include_router(tickets_router)
app.include_router(invoices_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
