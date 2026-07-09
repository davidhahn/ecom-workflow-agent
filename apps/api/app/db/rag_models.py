import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base
from app.rag.embeddings import EMBEDDING_DIM


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    source_doc: Mapped[str] = mapped_column(Text, nullable=False)
    rule_number: Mapped[int | None] = mapped_column(Integer)
