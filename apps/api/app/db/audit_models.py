import uuid

from sqlalchemy import CheckConstraint, Float, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class QueryAuditLog(Base):
    """Layer 4 — logs every SQL-path attempt, not just successes."""

    __tablename__ = "query_audit_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success','rejected','error')",
            name="query_audit_log_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text)
    stated_intent: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    layer_outcomes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
