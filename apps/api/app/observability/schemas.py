import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RequestLogRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_type: str
    input: str
    output: Any
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    grounded: bool | None
    sql_query_audit_id: uuid.UUID | None
    rag_chunks_retrieved: Any | None
    cached: bool
    created_at: datetime


class RequestLogListResponse(BaseModel):
    requests: list[RequestLogRow]
