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


class RefundEvaluateRequest(BaseModel):
    request_text: str


class RefundEvaluateResponse(BaseModel):
    status: str
    rule_applied: int | None
    reasoning: str
    extracted_fields: dict[str, Any]
