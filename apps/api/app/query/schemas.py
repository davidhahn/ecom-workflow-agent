from typing import Any, Literal

from pydantic import BaseModel


class SqlQueryRequest(BaseModel):
    question: str


class SqlQueryResponse(BaseModel):
    status: Literal["success", "rejected", "error"]
    sql_executed: str | None = None
    rejection_reason: str | None = None
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    truncated: bool = False
    execution_time_ms: int | None = None
    estimated_cost: float | None = None
