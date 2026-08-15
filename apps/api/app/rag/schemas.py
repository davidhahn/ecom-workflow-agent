from pydantic import BaseModel


class RagQueryRequest(BaseModel):
    question: str
    k: int = 3
    # Eval-only: skips the app cache for this call, same as AnalyzeRequest
    # and SqlQueryRequest's own bypass_cache. /query/rag never had one
    # before. query_rag() itself doesn't cache. The router wrapping it
    # does, and a comparison run needs a fresh answer every time it asks
    # the same question under a changed RELEVANCE_THRESHOLD.
    bypass_cache: bool = False


class RagChunkResult(BaseModel):
    content: str
    source_doc: str
    rule_number: int | None
    similarity: float


class RagQueryResponse(BaseModel):
    chunks: list[RagChunkResult]
    cached: bool = False
    # Set only when chunks is empty. No retrieved chunk cleared the
    # relevance threshold. This lets a caller show the outcome directly,
    # rather than guessing at what an empty list means.
    message: str | None = None


def chunk_from_dict(data: dict) -> RagChunkResult:
    """Reconstructs a RagChunkResult from a plain dict - e.g. an eval fixture
    loaded from JSON - into the typed shape check_groundedness() (and any
    other RagChunkResult consumer) actually expects, rather than each caller
    inventing its own dict-to-object workaround."""
    return RagChunkResult(**data)
