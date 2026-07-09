"""Re-runnable ingestion for the RAG policy corpus: chunk docs/policies/*.md,
embed locally with BAAI/bge-m3, and load into policy_chunks.

Usage:
    poetry run python -m app.rag.ingest
"""

import uuid
from pathlib import Path

from sqlalchemy import insert, text

from app.db.rag_models import PolicyChunk
from app.db.session import engine
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import embed

# apps/api/app/rag/ingest.py -> repo root is 4 levels up.
REPO_ROOT = Path(__file__).resolve().parents[4]
POLICIES_DIR = REPO_ROOT / "docs" / "policies"

DOCS = [
    ("refund_policy.md", True),
    ("shipping_policy.md", False),
    ("support_playbook.md", False),
]


def ingest() -> None:
    all_chunks = []
    for filename, numbered in DOCS:
        all_chunks.extend(chunk_markdown(POLICIES_DIR / filename, numbered=numbered))

    embeddings = embed([c.content for c in all_chunks])

    rows = [
        {
            "id": uuid.uuid4(),
            "content": chunk.content,
            "embedding": embedding,
            "source_doc": chunk.source_doc,
            "rule_number": chunk.rule_number,
        }
        for chunk, embedding in zip(all_chunks, embeddings)
    ]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE policy_chunks"))
        conn.execute(insert(PolicyChunk), rows)

    print(f"Ingested {len(rows)} policy chunks from {len(DOCS)} documents.")


if __name__ == "__main__":
    ingest()
