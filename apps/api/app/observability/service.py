from datetime import datetime

from sqlalchemy import select

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.observability.schemas import RequestLogRow

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def list_request_logs(
    *,
    request_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[RequestLogRow]:
    """Filtering and pagination only — no aggregation, grouping, or computed
    stats. That's Part 4 eval-harness work, not this step."""
    with SessionLocal() as session:
        stmt = select(RequestLog)
        if request_type is not None:
            stmt = stmt.where(RequestLog.request_type == request_type)
        if since is not None:
            stmt = stmt.where(RequestLog.created_at >= since)
        if until is not None:
            stmt = stmt.where(RequestLog.created_at <= until)
        stmt = stmt.order_by(RequestLog.created_at.desc()).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return [RequestLogRow.model_validate(row) for row in rows]
