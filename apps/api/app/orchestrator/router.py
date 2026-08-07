from fastapi import APIRouter, Request, Response

from app.orchestrator.analyze_service import analyze
from app.orchestrator.refund_service import evaluate_refund_request
from app.orchestrator.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    RefundEvaluateRequest,
    RefundEvaluateResponse,
)
from app.rate_limit import eval_bypass, limiter

router = APIRouter()


@router.post("/query/analyze", response_model=AnalyzeResponse)
@limiter.limit("10/hour", exempt_when=eval_bypass)
def analyze_endpoint(request: Request, response: Response, body: AnalyzeRequest) -> AnalyzeResponse:
    return analyze(body.question, bypass_cache=body.bypass_cache)


@router.post("/refund/evaluate", response_model=RefundEvaluateResponse)
@limiter.limit("15/hour", exempt_when=eval_bypass)
def refund_evaluate_endpoint(
    request: Request, response: Response, body: RefundEvaluateRequest
) -> RefundEvaluateResponse:
    # Decision only — this never writes to refunds. Executing the decision
    # (updating a refund's status) is a real production feature deliberately
    # not built in Part 1. Not cached (unlike the other three endpoints):
    # each request represents a distinct customer scenario, so a cached
    # decision would be misleading demo behavior.
    return evaluate_refund_request(body.request_text)
