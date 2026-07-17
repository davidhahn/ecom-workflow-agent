from typing import Any

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    question: str


class SourceRef(BaseModel):
    rule_number: int | None
    source_doc: str


class AnalyzeResponse(BaseModel):
    answer: str
    sql_used: bool
    rag_used: bool
    grounded: bool
    ungrounded_claims: list[str]
    sources: list[SourceRef]
    # True only when the tool-call loop was exhausted (MAX_TOOL_ITERATIONS
    # reached while Claude was still requesting tools) without ever reaching
    # a final answer. `answer` is then an explanatory message, not a real
    # answer, and `grounded`/`ungrounded_claims` were never evaluated against
    # it (an empty answer would trivially "pass" groundedness).
    incomplete: bool = False
    cached: bool = False
    # A separate, additional signal from check_groundedness()/grounded above:
    # true when the answer mentions a topic (shipment/delivery/tracking) the
    # current toolset has no way to actually answer, and no SQL call in this
    # request queried the shipments table. A citation can be grounded while
    # the answer's actual data claim is still fabricated from an unrelated
    # table — see app/orchestrator/topic_coverage.py.
    topic_coverage_warning: bool = False


class RefundEvaluateRequest(BaseModel):
    request_text: str


class RefundEvaluateResponse(BaseModel):
    status: str
    rule_applied: int | None
    reasoning: str
    extracted_fields: dict[str, Any]
