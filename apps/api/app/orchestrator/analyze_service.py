import json
import os

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL, ProposedQuery
from app.query.schema_context import build_schema_context
from app.query.service import execute_proposed_query
from app.query.tool_spec import RUN_SQL_QUERY_TOOL
from app.rag.service import query_rag
from app.rag.schemas import RagChunkResult
from app.orchestrator.groundedness import check_groundedness
from app.orchestrator.schemas import AnalyzeResponse, SourceRef
from app.orchestrator.tool_specs import SEARCH_POLICY_TOOL

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

Database schema:
{schema}
"""


def _run_search_policy_tool(tool_input: dict) -> list[RagChunkResult]:
    rag_response = query_rag(tool_input["query"], k=3)
    return rag_response.chunks


def _run_run_sql_query_tool(question: str, tool_input: dict) -> dict:
    proposed = ProposedQuery(query=tool_input["query"], intent=tool_input["intent"])
    sql_response = execute_proposed_query(question, proposed)
    return sql_response.model_dump(mode="json")


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
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    system = SYSTEM_PROMPT.format(schema=build_schema_context())

    messages: list[dict] = [{"role": "user", "content": question}]
    sql_used = False
    rag_used = False
    retrieved_chunks: list[RagChunkResult] = []

    response = None
    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            tools=[RUN_SQL_QUERY_TOOL, SEARCH_POLICY_TOOL],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "run_sql_query":
                sql_used = True
                result = _run_run_sql_query_tool(question, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                )
            elif block.name == "search_policy":
                rag_used = True
                chunks = _run_search_policy_tool(block.input)
                retrieved_chunks.extend(chunks)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps([c.model_dump() for c in chunks]),
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    answer = next((b.text for b in response.content if b.type == "text"), "") if response else ""

    grounded, ungrounded_claims = check_groundedness(answer, retrieved_chunks)

    return AnalyzeResponse(
        answer=answer,
        sql_used=sql_used,
        rag_used=rag_used,
        grounded=grounded,
        ungrounded_claims=ungrounded_claims,
        sources=_build_sources(retrieved_chunks),
    )
