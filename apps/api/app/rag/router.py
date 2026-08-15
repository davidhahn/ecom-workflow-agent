from fastapi import APIRouter, Depends, Request, Response

from app.caching.cache import cache_get, cache_set, normalize_key
from app.observability.logger import request_log_span
from app.permissions import require_permission
from app.rag.schemas import RagQueryRequest, RagQueryResponse
from app.rag.service import query_rag
from app.rate_limit import eval_bypass, limiter

router = APIRouter()

_CACHE_NAMESPACE = "rag"


@router.post("/query/rag", response_model=RagQueryResponse)
@limiter.limit("20/hour", exempt_when=eval_bypass)
def query_rag_endpoint(
    request: Request,
    response: Response,
    body: RagQueryRequest,
    role: str = Depends(require_permission("search_policy", "rag")),
) -> RagQueryResponse:
    # Logged here rather than inside query_rag() itself — that function is
    # also called internally by /query/analyze's search_policy tool, and
    # each request must write exactly one request_log row at its true entry
    # point, not one per internal RAG lookup. Caching lives at this same
    # entry point for the same reason: analyze()'s internal RAG calls must
    # not be affected by this endpoint's cache.
    with request_log_span("rag", body.question) as log:
        cache_key = normalize_key(body.question)
        cached = None if body.bypass_cache else cache_get(_CACHE_NAMESPACE, cache_key)
        if cached is not None:
            log.cached = True
            log.input_tokens = 0
            log.output_tokens = 0
            response = cached.model_copy(update={"cached": True})
            log.output = response.model_dump(mode="json")
            return response

        response = query_rag(body.question, k=body.k)
        log.output = response.model_dump(mode="json")
        log.rag_chunks_retrieved = [c.model_dump(mode="json") for c in response.chunks]
        if not body.bypass_cache:
            cache_set(_CACHE_NAMESPACE, cache_key, response)
        return response
