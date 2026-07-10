from fastapi import APIRouter

from app.orchestrator.analyze_service import analyze
from app.orchestrator.refund_service import evaluate_refund_request
from app.orchestrator.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    RefundEvaluateRequest,
    RefundEvaluateResponse,
)

router = APIRouter()


@router.post("/query/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest) -> AnalyzeResponse:
    return analyze(request.question)


@router.post("/refund/evaluate", response_model=RefundEvaluateResponse)
def refund_evaluate_endpoint(request: RefundEvaluateRequest) -> RefundEvaluateResponse:
    # Decision only — this never writes to refunds. Executing the decision
    # (updating a refund's status) is a real production feature deliberately
    # not built in Part 1.
    return evaluate_refund_request(request.request_text)
