from sentence_transformers import SentenceTransformer

EMBEDDING_DIM = 1024

# Local sentence-transformers model (BAAI/bge-m3), not an external embedding
# API. This is a scope-specific choice: the corpus is ~17 policy chunks,
# fixed and small, so there's no scaling problem to outsource to a hosted
# embedding service. Do not carry this choice forward unexamined if the
# corpus grows to thousands of documents, needs multilingual/rerank tuning,
# or the local model becomes an infra burden — re-evaluate hosted embedding
# APIs and an ANN index (ivfflat/hnsw) at that point.
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
