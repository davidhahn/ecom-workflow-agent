from fastapi import APIRouter

from app.observability.logger import request_log_span
from app.rag.schemas import RagQueryRequest, RagQueryResponse
from app.rag.service import query_rag

router = APIRouter()


@router.post("/query/rag", response_model=RagQueryResponse)
def query_rag_endpoint(request: RagQueryRequest) -> RagQueryResponse:
    # Logged here rather than inside query_rag() itself — that function is
    # also called internally by /query/analyze's search_policy tool, and
    # each request must write exactly one request_log row at its true entry
    # point, not one per internal RAG lookup.
    with request_log_span("rag", request.question) as log:
        response = query_rag(request.question, k=request.k)
        log.output = response.model_dump(mode="json")
        log.rag_chunks_retrieved = [c.model_dump(mode="json") for c in response.chunks]
        return response
