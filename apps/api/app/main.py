from fastapi import FastAPI

from app.query.router import router as query_router

app = FastAPI(title="Ops Intelligence Agent API")
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
