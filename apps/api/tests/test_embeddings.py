"""Tests for the EMBEDDING_PROVIDER dispatch in app/rag/embeddings.py
(DECISIONS.md #8): local BAAI/bge-m3 (dev default) vs. hosted Voyage AI
(deploy). The local-provider test hits the real sentence-transformers model,
same as test_tool_registry.py's RAG coverage. The voyage-provider tests mock
the HTTP call rather than hitting the real API."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.rag.embeddings import EMBEDDING_DIM, VOYAGE_MODEL, embed_one

API_ROOT = Path(__file__).resolve().parents[1]


def test_local_provider_returns_correct_dimension(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    vector = embed_one("What is the standard return window?")
    assert len(vector) == EMBEDDING_DIM


def test_voyage_provider_returns_correct_dimension(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "voyage")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"data": [{"embedding": [0.1] * EMBEDDING_DIM}]}

    with patch("app.rag.embeddings.httpx.post", return_value=fake_response) as mock_post:
        vector = embed_one("What is the standard return window?")

    assert len(vector) == EMBEDDING_DIM
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == VOYAGE_MODEL
    assert kwargs["json"]["output_dimension"] == EMBEDDING_DIM
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_voyage_provider_never_imports_torch_or_sentence_transformers():
    """The critical constraint: EMBEDDING_PROVIDER=voyage must never import
    sentence_transformers/torch, not even lazily — that import alone is the
    memory allocation this provider split exists to avoid. Run in a fresh
    subprocess rather than in-process, since the local-provider test above
    may already have imported sentence_transformers into this test session's
    sys.modules, which would make an in-process check meaningless."""
    script = """
import os
os.environ["EMBEDDING_PROVIDER"] = "voyage"
os.environ["VOYAGE_API_KEY"] = "test-key"

import sys
from unittest.mock import MagicMock, patch
import app.rag.embeddings as e

fake_response = MagicMock()
fake_response.raise_for_status.return_value = None
fake_response.json.return_value = {"data": [{"embedding": [0.1] * e.EMBEDDING_DIM}]}

with patch("app.rag.embeddings.httpx.post", return_value=fake_response):
    e.embed_one("test")

bad = [
    m for m in sys.modules
    if m == "torch" or m == "sentence_transformers"
    or m.startswith("torch.") or m.startswith("sentence_transformers.")
]
print("BAD:" + ",".join(bad) if bad else "CLEAN")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CLEAN", result.stdout
