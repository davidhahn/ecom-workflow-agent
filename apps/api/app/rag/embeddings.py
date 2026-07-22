import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

EMBEDDING_DIM = 1024
VOYAGE_MODEL = "voyage-3.5-lite"
VOYAGE_EMBEDDINGS_URL = "https://api.voyageai.com/v1/embeddings"

# EMBEDDING_PROVIDER selects the embedding source; see DECISIONS.md #8. "local"
# (default) is BAAI/bge-m3 via sentence-transformers, free and network-free,
# used in dev. "voyage" is the hosted Voyage AI API, used in deploy where
# sentence-transformers' torch dependency is a memory cost the environment
# can't absorb. output_dimension is pinned to EMBEDDING_DIM explicitly on the
# voyage request so a future API default change can't silently produce a
# vector that no longer matches policy_chunks.embedding's fixed vector(1024)
# column.
#
# Critical: sentence_transformers/torch must never be imported when
# EMBEDDING_PROVIDER=voyage, not even lazily — that import alone is the
# memory allocation deploy is trying to avoid. This is why the voyage path is
# a direct HTTP call (httpx) rather than the `voyageai` SDK: that package's
# own __init__.py unconditionally imports langchain_text_splitters, which —
# whenever sentence-transformers is also installed in the same environment,
# as it is here for the local dev path — transitively imports
# sentence_transformers and therefore torch, even if voyage's Client is never
# instantiated. A bare `import voyageai` alone was enough to trigger it
# (verified by tracing the import chain), so the only way to guarantee zero
# torch import on this path is to not import that package at all.
_model: "SentenceTransformer | None" = None


def _provider() -> str:
    return os.environ.get("EMBEDDING_PROVIDER", "local")


def _get_local_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


def _embed_voyage(texts: list[str]) -> list[list[float]]:
    api_key = os.environ["VOYAGE_API_KEY"]
    response = httpx.post(
        VOYAGE_EMBEDDINGS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "input": texts,
            "model": VOYAGE_MODEL,
            "output_dimension": EMBEDDING_DIM,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def embed(texts: list[str]) -> list[list[float]]:
    provider = _provider()
    if provider == "local":
        return _embed_local(texts)
    elif provider == "voyage":
        return _embed_voyage(texts)
    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER '{provider}' — must be 'local' or 'voyage'."
        )


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
