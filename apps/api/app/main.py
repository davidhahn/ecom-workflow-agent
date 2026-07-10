from fastapi import FastAPI

from app.orchestrator.router import router as orchestrator_router
from app.query.router import router as query_router
from app.rag.router import router as rag_router

app = FastAPI(title="Ops Intelligence Agent API")
app.include_router(query_router)
app.include_router(rag_router)
app.include_router(orchestrator_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
