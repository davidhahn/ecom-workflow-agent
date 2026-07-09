from fastapi import APIRouter

from app.rag.schemas import RagQueryRequest, RagQueryResponse
from app.rag.service import query_rag

router = APIRouter()


@router.post("/query/rag", response_model=RagQueryResponse)
def query_rag_endpoint(request: RagQueryRequest) -> RagQueryResponse:
    return query_rag(request.question, k=request.k)
