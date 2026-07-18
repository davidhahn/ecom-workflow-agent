import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class RequestLog(Base):
    """Unified request log across all four endpoints. App-written only
    (never LLM-generated); read via GET /observability/requests. Feeds the
    Part 4 eval harness later — grounded and rag_chunks_retrieved are kept
    as separate typed columns rather than folded into `output` specifically
    so Part 4 doesn't have to parse them back out of an opaque blob."""

    __tablename__ = "request_log"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('sql','rag','analyze','refund_evaluate',"
            "'ticket_draft','ticket_confirm')",
            name="request_log_request_type_check",
        ),
        Index("ix_request_log_request_type", "request_type"),
        Index("ix_request_log_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    request_type: Mapped[str] = mapped_column(Text, nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    grounded: Mapped[bool | None] = mapped_column(Boolean)
    sql_query_audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_audit_log.id")
    )
    # none_as_null=True: SQLAlchemy's JSON/JSONB defaults to serializing a
    # Python None as the JSON literal `null` (a real, non-NULL JSONB value),
    # not SQL NULL. Without this, every non-RAG row would store `null` here
    # instead of leaving the column genuinely NULL.
    rag_chunks_retrieved: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
