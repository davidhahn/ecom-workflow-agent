"""Re-runnable ingestion for the RAG corpus: chunk docs/**/*.md, embed
locally with BAAI/bge-m3, and load into policy_chunks.

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
DOCS_DIR = REPO_ROOT / "docs"

# Paths are relative to DOCS_DIR, not assumed to all live in one flat
# subdirectory — docs/notes/ sits alongside docs/policies/ here.
DOCS = [
    ("policies/refund_policy.md", True),
    ("policies/shipping_policy.md", False),
    ("policies/support_playbook.md", False),
    ("notes/campaign-launch-notes.md", False),
]


def ingest() -> None:
    all_chunks = []
    for relative_path, numbered in DOCS:
        all_chunks.extend(chunk_markdown(DOCS_DIR / relative_path, numbered=numbered))

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
