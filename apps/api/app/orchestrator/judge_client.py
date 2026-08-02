import json
import os
import re
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL

load_dotenv()

JUDGE_PROMPT_TEMPLATE = """You are evaluating an AI assistant's answer.

Grade only against the checklist below.
Ignore writing style, length, tone, and confidence unless the checklist
explicitly mentions them.

QUESTION:
{case_input}

ANSWER TO EVALUATE:
{actual_answer}

REQUIRED KEY POINTS:
{key_points_block}

For each key point, decide whether the answer clearly covers it.
Return a brief evidence summary. Do not add requirements that are not
listed in the rubric.

Return only valid JSON:

{{
  "points_covered": [1, 2],
  "points_missed": [3],
  "verdict": "pass",
  "evidence_summary": "The answer explains points 1 and 2 but never addresses point 3."
}}
"""

REQUIRED_VERDICT_KEYS = {"points_covered", "points_missed", "verdict", "evidence_summary"}

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Models routinely wrap JSON in a ```json fence despite being told to
    return only JSON. This is tolerant parsing of the one response already
    received, not a retry — the API is never called again here."""
    match = _FENCE_RE.match(text.strip())
    return match.group(1) if match else text


@dataclass
class JudgeVerdict:
    points_covered: list[int]
    points_missed: list[int]
    verdict: str  # "pass" | "fail", as self-reported by the judge
    evidence_summary: str


@dataclass
class JudgeResult:
    # verdict is None exactly when judge_error is set — an unparseable or
    # incomplete judge response is recorded as data, never silently retried
    # or coerced into a verdict just because the format was inconvenient.
    verdict: JudgeVerdict | None
    judge_error: str | None
    raw_response: str


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def judge_answer(case_input: str, actual_answer: str, key_points: list[str]) -> JudgeResult:
    client = _client()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    key_points_block = "\n".join(f"{i}. {point}" for i, point in enumerate(key_points, start=1))
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        case_input=case_input, actual_answer=actual_answer, key_points_block=key_points_block
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_response = next((block.text for block in response.content if block.type == "text"), "")

    try:
        parsed = json.loads(_strip_code_fence(raw_response))
    except json.JSONDecodeError as e:
        return JudgeResult(verdict=None, judge_error=f"invalid JSON from judge: {e}", raw_response=raw_response)

    if not isinstance(parsed, dict) or not REQUIRED_VERDICT_KEYS.issubset(parsed.keys()):
        missing = REQUIRED_VERDICT_KEYS - (parsed.keys() if isinstance(parsed, dict) else set())
        return JudgeResult(
            verdict=None,
            judge_error=f"judge JSON missing required keys: {sorted(missing)}",
            raw_response=raw_response,
        )

    verdict = JudgeVerdict(
        points_covered=parsed["points_covered"],
        points_missed=parsed["points_missed"],
        verdict=parsed["verdict"],
        evidence_summary=parsed["evidence_summary"],
    )
    return JudgeResult(verdict=verdict, judge_error=None, raw_response=raw_response)
