"""Tests for the groundedness eval cases in evals/cases.json.

Loads the "groundedness" cases and runs each through the real
check_groundedness() function - not a schema check on the fixture, an actual
call - parametrized so each case shows up as its own named test in pytest
output (ground-01-..., ground-02-...) rather than one test looping silently
over both.
"""

import json
from pathlib import Path

import pytest

from app.orchestrator.groundedness import check_groundedness
from app.rag.schemas import chunk_from_dict

# apps/api/tests/test_groundedness_evals.py -> repo root is 3 levels up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CASES_PATH = _REPO_ROOT / "evals" / "cases.json"

with open(_CASES_PATH) as f:
    _ALL_CASES = json.load(f)

GROUNDEDNESS_CASES = [c for c in _ALL_CASES if c["category"] == "groundedness"]


@pytest.mark.parametrize("case", GROUNDEDNESS_CASES, ids=[c["id"] for c in GROUNDEDNESS_CASES])
def test_groundedness_eval_case(case):
    fixture = json.loads(case["input"])
    # retrieved_chunks in the fixture are plain JSON dicts (JSON can't
    # represent RagChunkResult directly); reconstruct the typed shape
    # check_groundedness() actually requires attribute access on.
    chunks = [chunk_from_dict(chunk) for chunk in fixture["retrieved_chunks"]]

    grounded, ungrounded_claims = check_groundedness(fixture["answer"], chunks)

    assert grounded == case["expected"]["grounded"], (
        f"{case['id']}: expected grounded={case['expected']['grounded']}, "
        f"got {grounded}; ungrounded_claims={ungrounded_claims}"
    )
