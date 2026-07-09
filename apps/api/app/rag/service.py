from sqlalchemy import select

from app.db.rag_models import PolicyChunk
from app.db.session import SessionLocal
from app.rag.embeddings import embed_one
from app.rag.schemas import RagChunkResult, RagQueryResponse

DEFAULT_K = 3


def query_rag(question: str, k: int = DEFAULT_K) -> RagQueryResponse:
    query_embedding = embed_one(question)

    with SessionLocal() as session:
        distance = PolicyChunk.embedding.cosine_distance(query_embedding)
        stmt = select(PolicyChunk, distance.label("distance")).order_by(distance).limit(k)
        rows = session.execute(stmt).all()

    return RagQueryResponse(
        chunks=[
            RagChunkResult(
                content=chunk.content,
                source_doc=chunk.source_doc,
                rule_number=chunk.rule_number,
                similarity=1.0 - distance,
            )
            for chunk, distance in rows
        ]
    )
