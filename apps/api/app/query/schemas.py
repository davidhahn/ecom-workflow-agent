from typing import Any, Literal

from pydantic import BaseModel


class SqlQueryRequest(BaseModel):
    question: str
    # Eval-only: skips the app cache for this call - see AnalyzeRequest's
    # bypass_cache. Off by default.
    bypass_cache: bool = False


class SqlQueryResponse(BaseModel):
    status: Literal["success", "rejected", "error"]
    sql_executed: str | None = None
    rejection_reason: str | None = None
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    truncated: bool = False
    execution_time_ms: int | None = None
    estimated_cost: float | None = None
    cached: bool = False
    # Which prompt version generated this query. None if nothing was
    # ever proposed (e.g. Claude never returned a tool call).
    prompt_version: str | None = None
