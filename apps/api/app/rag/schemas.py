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
