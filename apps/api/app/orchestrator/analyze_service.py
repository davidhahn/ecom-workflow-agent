import json
import os
import time

import anthropic
from dotenv import load_dotenv

from app.caching.cache import cache_get, cache_set, normalize_key
from app.observability.logger import request_log_span
from app.observability.schemas import ToolCallEntry
from app.query.claude_client import DEFAULT_MODEL, ProposedQuery
from app.query.schema_context import build_schema_context
from app.query.service import ExecutedQuery, execute_proposed_query
from app.rag.service import query_rag
from app.rag.schemas import RagChunkResult
from app.orchestrator.groundedness import check_groundedness
from app.orchestrator.schemas import AnalyzeResponse, SourceRef
from app.orchestrator.topic_coverage import check_topic_coverage
from app.tools.registry import anthropic_tool_defs

load_dotenv()

MAX_TOOL_ITERATIONS = 4

SYSTEM_PROMPT = """You are an ops assistant for an eCommerce company. Answer \
the user's question using the tools available:

- run_sql_query: query the live ops database for factual/analytical answers \
(counts, rates, specific records). A single read-only SELECT statement, \
explicit columns only, never SELECT *. The customers table's email column \
is not available to you and must never appear in your query.
- search_policy: search company policy documents (refund policy, shipping \
policy, support playbook) for rules and guidance.

Call whichever tool(s) are actually relevant to the question — both if it \
needs data and policy context together, one if it only needs one, neither \
if you can answer directly. When your final answer relies on a specific \
numbered refund-policy rule, cite it explicitly as "rule N" so the citation \
can be checked against what was actually retrieved.

You do not currently have access to shipment tracking, delivery delay \
status, or carrier data. If a question is about shipment delays, tracking, \
or delivery status, say so explicitly rather than inferring an answer from \
order status or any other adjacent data.

Only make claims backed by an actual tool result. If no tool result \
directly addresses the question, state that clearly rather than \
speculating from related information.

This is an enterprise ops tool. Write your final answer in plain \
professional prose — no emoji.

Database schema:
{schema}
"""


def _run_search_policy_tool(tool_input: dict) -> list[RagChunkResult]:
    rag_response = query_rag(tool_input["query"], k=3)
    return rag_response.chunks


def _run_run_sql_query_tool(question: str, tool_input: dict) -> ExecutedQuery:
    proposed = ProposedQuery(query=tool_input["query"], intent=tool_input["intent"])
    return execute_proposed_query(question, proposed)


def _build_sources(chunks: list[RagChunkResult]) -> list[SourceRef]:
    seen: set[tuple[int | None, str]] = set()
    sources: list[SourceRef] = []
    for chunk in chunks:
        key = (chunk.rule_number, chunk.source_doc)
        if key in seen:
            continue
        seen.add(key)
        sources.append(SourceRef(rule_number=chunk.rule_number, source_doc=chunk.source_doc))
    return sources


def analyze(question: str) -> AnalyzeResponse:
    with request_log_span("analyze", question) as log:
        cache_key = normalize_key(question)
        cached = cache_get("analyze", cache_key)
        if cached is not None:
            log.cached = True
            log.input_tokens = 0
            log.output_tokens = 0
            # No tool loop ran for this request (served from cache) — an
            # empty trace, not NULL, since this is still request_type
            # 'analyze' and every analyze row logs a (possibly empty) array.
            log.tool_calls = []
            result = cached.model_copy(update={"cached": True})
            log.output = result.model_dump(mode="json")
            return result

        client = anthropic.Anthropic()
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        system = SYSTEM_PROMPT.format(schema=build_schema_context())

        messages: list[dict] = [{"role": "user", "content": question}]
        sql_used = False
        rag_used = False
        retrieved_chunks: list[RagChunkResult] = []
        generated_sql: list[str] = []
        # Accumulated across every iteration of the loop below, not reset
        # per iteration — sequence numbers must reflect the call's position
        # in the whole request, not just within one turn.
        tool_calls: list[dict] = []

        response = None
        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system,
                tools=anthropic_tool_defs(for_analyze=True),
                messages=messages,
            )
            log.add_usage(response.usage)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                call_start = time.perf_counter()
                if block.name == "run_sql_query":
                    sql_used = True
                    executed = _run_run_sql_query_tool(question, block.input)
                    log.sql_query_audit_id = executed.audit_id
                    if executed.response.sql_executed:
                        generated_sql.append(executed.response.sql_executed)
                    result = executed.response.model_dump(mode="json")
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                    )
                    tool_calls.append(
                        ToolCallEntry(
                            tool_name=block.name,
                            input=block.input,
                            output=result,
                            latency_ms=int((time.perf_counter() - call_start) * 1000),
                            sequence=len(tool_calls),
                        ).model_dump(mode="json")
                    )
                elif block.name == "search_policy":
                    rag_used = True
                    chunks = _run_search_policy_tool(block.input)
                    retrieved_chunks.extend(chunks)
                    chunk_dicts = [c.model_dump() for c in chunks]
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(chunk_dicts),
                        }
                    )
                    tool_calls.append(
                        ToolCallEntry(
                            tool_name=block.name,
                            input=block.input,
                            output=chunk_dicts,
                            latency_ms=int((time.perf_counter() - call_start) * 1000),
                            sequence=len(tool_calls),
                        ).model_dump(mode="json")
                    )
            messages.append({"role": "user", "content": tool_results})
        else:
            # Loop ran MAX_TOOL_ITERATIONS times and never hit the `break`
            # above — Claude was still requesting tools on the last call and
            # never reached a final answer. Must not fall through to the
            # normal path below: an empty `answer` would trivially "pass"
            # check_groundedness (nothing to flag as ungrounded), rendering
            # as a blank answer with a misleading "grounded" badge instead of
            # a visible failure. Skip the check entirely and return a
            # distinct, explicit incomplete state instead.
            result = AnalyzeResponse(
                answer=(
                    "This request could not be completed: the assistant was still "
                    "requesting tools after the maximum number of tool-call rounds "
                    "and never reached a final answer."
                ),
                sql_used=sql_used,
                rag_used=rag_used,
                grounded=False,
                ungrounded_claims=[],
                sources=_build_sources(retrieved_chunks),
                incomplete=True,
            )
            # Whatever calls completed before exhaustion — a valid, ordered
            # (possibly empty) array, never a broken/partial structure, since
            # entries are only ever appended fully-formed after each call
            # finishes.
            log.tool_calls = tool_calls
            log.output = result.model_dump(mode="json")
            return result

        answer = next((b.text for b in response.content if b.type == "text"), "")

        grounded, ungrounded_claims = check_groundedness(answer, retrieved_chunks)
        log.grounded = grounded
        if retrieved_chunks:
            log.rag_chunks_retrieved = [c.model_dump(mode="json") for c in retrieved_chunks]

        # Separate, additional check from check_groundedness() above — a
        # citation can check out (grounded=True) while the answer's actual
        # data-driven claim is still fabricated from an unrelated table. See
        # app/orchestrator/topic_coverage.py.
        topic_coverage_warning = check_topic_coverage(answer, sql_used, generated_sql)

        result = AnalyzeResponse(
            answer=answer,
            sql_used=sql_used,
            rag_used=rag_used,
            grounded=grounded,
            ungrounded_claims=ungrounded_claims,
            sources=_build_sources(retrieved_chunks),
            topic_coverage_warning=topic_coverage_warning,
        )
        log.tool_calls = tool_calls
        log.output = result.model_dump(mode="json")
        cache_set("analyze", cache_key, result)
        return result
