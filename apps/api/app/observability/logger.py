import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.observability.pricing import estimate_cost_usd


@dataclass
class LogFields:
    """Mutable accumulator yielded by request_log_span. Set whatever fields
    become available as the request executes; request_log_span writes
    exactly one row from whatever's set when the `with` block exits, success
    or failure. Anything never set is logged as NULL rather than guessed."""

    output: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    grounded: bool | None = None
    sql_query_audit_id: uuid.UUID | None = None
    rag_chunks_retrieved: list[Any] | None = None

    def add_usage(self, usage: Any) -> None:
        """Accumulates an Anthropic response.usage. Safe to call multiple
        times per request — /query/analyze's tool loop can make several
        Claude calls — or never, for the LLM-free /query/rag path."""
        if usage is None:
            return
        self.input_tokens = (self.input_tokens or 0) + usage.input_tokens
        self.output_tokens = (self.output_tokens or 0) + usage.output_tokens


def log_request(
    *,
    request_type: str,
    input_text: str,
    output: dict[str, Any],
    latency_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    grounded: bool | None = None,
    sql_query_audit_id: uuid.UUID | None = None,
    rag_chunks_retrieved: list[Any] | None = None,
) -> uuid.UUID:
    log_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(
            RequestLog(
                id=log_id,
                request_type=request_type,
                input=input_text,
                output=output,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens),
                grounded=grounded,
                sql_query_audit_id=sql_query_audit_id,
                rag_chunks_retrieved=rag_chunks_retrieved,
            )
        )
        session.commit()
    return log_id


@contextmanager
def request_log_span(request_type: str, input_text: str) -> Iterator[LogFields]:
    """Times a request and writes exactly one request_log row when the with
    block exits, success or failure — including on an unhandled exception,
    which still re-raises after logging (this never swallows a real error,
    it just also logs it)."""
    start = time.perf_counter()
    fields = LogFields()
    try:
        yield fields
    except Exception as e:
        if fields.output is None:
            fields.output = {"error": str(e)}
        raise
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_request(
            request_type=request_type,
            input_text=input_text,
            output=fields.output if fields.output is not None else {},
            latency_ms=latency_ms,
            input_tokens=fields.input_tokens,
            output_tokens=fields.output_tokens,
            grounded=fields.grounded,
            sql_query_audit_id=fields.sql_query_audit_id,
            rag_chunks_retrieved=fields.rag_chunks_retrieved,
        )
