from fastapi import FastAPI

app = FastAPI(title="Ops Intelligence Agent API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
