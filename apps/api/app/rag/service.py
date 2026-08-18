from sqlalchemy import select

from app.db.rag_models import PolicyChunk
from app.db.session import SessionLocal
from app.rag.embeddings import embed_one, embedding_provider
from app.rag.schemas import RagChunkResult, RagQueryResponse

DEFAULT_K = 3

# Cosine distance cutoff for relevant evidence, one per embedding provider.
# A distance means something different in each embedding space, so the same
# cutoff number can't serve both. "local" comes from
# evals/rag_retrieval_calibration.md: 0.46 was the tightest value that kept
# every relevant example in that calibration set. "voyage" is what
# production actually runs (render.yaml), and was recalibrated after a live
# question got wrongly rejected under the local-tuned value: 0.46 missed a
# real example that landed at 0.4779 under voyage. 0.48 is the tightest
# voyage value with the same property, zero missed relevant examples. Past
# the cutoff for whichever provider is active, treat a question as
# unsupported by the policy corpus.
RELEVANCE_THRESHOLD_BY_PROVIDER = {"local": 0.46, "voyage": 0.48}
RELEVANCE_THRESHOLD = RELEVANCE_THRESHOLD_BY_PROVIDER[embedding_provider()]

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
