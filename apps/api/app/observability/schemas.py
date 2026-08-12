import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ToolCallEntry(BaseModel):
    """One tool invocation within /query/analyze's tool-call loop. sequence
    is the call's position across the *entire* loop (all iterations), not
    reset per iteration, so the ordered trace survives even when the loop
    calls multiple tools in one turn or spans several turns."""

    tool_name: str
    input: dict[str, Any]
    output: Any
    latency_ms: int
    sequence: int


class RequestLogRow(BaseModel):
    """Summary shape used by the list endpoint. Deliberately excludes
    tool_calls — a full per-call trace is only meaningful for one request at
    a time, and including it on every row of a list response would bloat a
    50-row page with payloads nobody's looking at yet. See
    RequestLogDetailRow for the single-row detail endpoint."""

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
    retry_count: int | None
    created_at: datetime


class RequestLogDetailRow(RequestLogRow):
    """Full single-row detail, returned by GET /observability/requests/{id}.
    tool_calls is NULL for every request type except 'analyze' — see the
    column comment on RequestLog.tool_calls."""

    tool_calls: list[ToolCallEntry] | None


class RequestLogListResponse(BaseModel):
    requests: list[RequestLogRow]
