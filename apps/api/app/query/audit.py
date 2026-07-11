import uuid

from app.db.audit_models import QueryAuditLog
from app.db.session import SessionLocal


def record_attempt(
    *,
    question: str,
    generated_sql: str | None,
    stated_intent: str | None,
    status: str,
    layer_outcomes: dict,
    rejection_reason: str | None = None,
    row_count: int | None = None,
    execution_time_ms: int | None = None,
    estimated_cost: float | None = None,
) -> uuid.UUID:
    """Layer 4 — log this attempt regardless of outcome. Uses the normal app
    DB connection (not the restricted ops_agent_readonly role, which has no
    write access). Returns the generated row's id so callers can cross-
    reference it (e.g. request_log.sql_query_audit_id)."""
    audit_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(
            QueryAuditLog(
                id=audit_id,
                question=question,
                generated_sql=generated_sql,
                stated_intent=stated_intent,
                status=status,
                rejection_reason=rejection_reason,
                layer_outcomes=layer_outcomes,
                row_count=row_count,
                execution_time_ms=execution_time_ms,
                estimated_cost=estimated_cost,
            )
        )
        session.commit()
    return audit_id
