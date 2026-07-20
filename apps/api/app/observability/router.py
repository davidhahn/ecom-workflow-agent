import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.observability.schemas import RequestLogDetailRow, RequestLogListResponse
from app.observability.service import MAX_LIMIT, get_request_log, list_request_logs

router = APIRouter()

RequestType = Literal[
    "sql", "rag", "analyze", "refund_evaluate", "ticket_draft", "ticket_confirm"
]


@router.get("/observability/requests", response_model=RequestLogListResponse)
def list_requests_endpoint(
    request_type: RequestType | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, gt=0, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> RequestLogListResponse:
    rows = list_request_logs(
        request_type=request_type, since=since, until=until, limit=limit, offset=offset
    )
    return RequestLogListResponse(requests=rows)


@router.get("/observability/requests/{request_id}", response_model=RequestLogDetailRow)
def get_request_endpoint(request_id: uuid.UUID) -> RequestLogDetailRow:
    row = get_request_log(request_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No request found for id '{request_id}'")
    return row
