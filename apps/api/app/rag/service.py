from sqlalchemy import select

from app.db.rag_models import PolicyChunk
from app.db.session import SessionLocal
from app.rag.embeddings import embed_one
from app.rag.schemas import RagChunkResult, RagQueryResponse

DEFAULT_K = 3

# Cosine distance cutoff for relevant evidence. Calibrated in
# evals/rag_retrieval_calibration.md, where 0.46 was the tightest value
# that still kept every clearly relevant example in the calibration set.
# Past this cutoff, treat a question as unsupported by the policy corpus.
RELEVANCE_THRESHOLD = 0.46

NO_RELEVANT_EVIDENCE_MESSAGE = "No sufficiently relevant policy information was found for this question."


def query_rag(question: str, k: int = DEFAULT_K) -> RagQueryResponse:
    query_embedding = embed_one(question)

    with SessionLocal() as session:
        distance = PolicyChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(PolicyChunk, distance.label("distance"))
            .where(distance <= RELEVANCE_THRESHOLD)
            .order_by(distance)
            .limit(k)
        )
        rows = session.execute(stmt).all()

    chunks = [
        RagChunkResult(
            content=chunk.content,
            source_doc=chunk.source_doc,
            rule_number=chunk.rule_number,
            similarity=1.0 - distance,
        )
        for chunk, distance in rows
    ]

    return RagQueryResponse(
        chunks=chunks,
        message=None if chunks else NO_RELEVANT_EVIDENCE_MESSAGE,
    )
