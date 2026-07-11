import os
from dataclasses import dataclass
from typing import Any

import anthropic
from dotenv import load_dotenv

from app.query.schema_context import build_schema_context
from app.query.tool_spec import RUN_SQL_QUERY_TOOL

load_dotenv()

# Pinned per ARCHITECTURE.md's "Orchestration" row. Overridable via env without
# a code change if that pin is revisited.
DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a SQL analyst for an eCommerce operations database.

Given a business question, call run_sql_query with a single read-only SELECT
statement that answers it, using only the tables and columns below. Always
list columns explicitly — never use SELECT *. The customers table's email
column is not available to you and must never appear in your query.

Schema:
{schema}
"""


@dataclass
class ProposedQuery:
    query: str
    intent: str
    # Anthropic response.usage from the call that produced this proposal —
    # None when constructed manually (e.g. from a tool call already made
    # elsewhere, as /query/analyze does), since there's no second Claude
    # call to attribute usage to in that case.
    usage: Any = None


class ClaudeProposalError(Exception):
    pass


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def propose_sql(question: str) -> ProposedQuery:
    client = _client()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(schema=build_schema_context()),
        tools=[RUN_SQL_QUERY_TOOL],
        tool_choice={"type": "tool", "name": "run_sql_query"},
        messages=[{"role": "user", "content": question}],
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"), None
    )
    if tool_use is None:
        raise ClaudeProposalError(
            f"Claude did not return a run_sql_query tool call (stop_reason={response.stop_reason})"
        )

    query = tool_use.input.get("query")
    intent = tool_use.input.get("intent")
    if not query or not intent:
        raise ClaudeProposalError(
            f"run_sql_query tool call missing required fields: {tool_use.input}"
        )

    return ProposedQuery(query=query, intent=intent, usage=response.usage)
