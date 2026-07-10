import re
from pathlib import Path

from app.rag.chunking import chunk_markdown
from app.rag.schemas import RagChunkResult

_RULE_NUMBER_RE = re.compile(r"\brule\s*#?\s*(\d+)\b", re.IGNORECASE)

# apps/api/app/orchestrator/groundedness.py -> repo root is 4 levels up.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_REFUND_POLICY_PATH = _REPO_ROOT / "docs" / "policies" / "refund_policy.md"


def _normalize(text: str) -> str:
    return re.sub(r"[-\s]+", " ", text.lower()).strip()


def _load_rule_titles() -> dict[str, int]:
    """Map normalized refund_policy.md rule titles -> rule_number, so a named
    citation ("per the final-sale exclusion") can be checked structurally
    even without an explicit rule number in the answer text. Derived from
    the same chunker RAG ingestion uses, not a hand-maintained duplicate."""
    chunks = chunk_markdown(_REFUND_POLICY_PATH, numbered=True)
    titles: dict[str, int] = {}
    for chunk in chunks:
        heading = chunk.content.split("\n", 1)[0]
        if chunk.rule_number is not None:
            titles[_normalize(heading)] = chunk.rule_number
    return titles


_RULE_TITLES = _load_rule_titles()


def _claimed_rule_numbers(answer: str) -> set[int]:
    claimed = {int(n) for n in _RULE_NUMBER_RE.findall(answer)}

    normalized_answer = _normalize(answer)
    for title, rule_number in _RULE_TITLES.items():
        if title in normalized_answer:
            claimed.add(rule_number)

    return claimed


def check_groundedness(
    answer: str, retrieved_chunks: list[RagChunkResult]
) -> tuple[bool, list[str]]:
    """Structural groundedness check — no LLM judge. Parses the answer for
    rule-number citations (numeric, e.g. "rule 9", or named, e.g. "the
    final-sale exclusion") and cross-checks each against the rule_number
    values actually present in the RAG chunks retrieved for this request.

    This is intentionally a substring/regex heuristic, not semantic
    understanding — it will miss paraphrased citations and can rarely
    false-positive on a title phrase used generically rather than as a
    citation. That tradeoff is the point: it's checking retrieval, not
    reading comprehension.
    """
    retrieved_rule_numbers = {
        chunk.rule_number for chunk in retrieved_chunks if chunk.rule_number is not None
    }
    claimed = _claimed_rule_numbers(answer)
    ungrounded = sorted(claimed - retrieved_rule_numbers)

    ungrounded_claims = [
        f"answer cites rule {n}, which was not among the retrieved policy chunks"
        for n in ungrounded
    ]
    return (len(ungrounded_claims) == 0, ungrounded_claims)
