from pydantic import BaseModel


class RagQueryRequest(BaseModel):
    question: str
    k: int = 3


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
