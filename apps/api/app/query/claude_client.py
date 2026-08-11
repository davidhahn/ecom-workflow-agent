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

# Bump this whenever SYSTEM_PROMPT changes. Recorded on every ProposedQuery,
# query_audit_log row, and SqlQueryResponse, so reports and traces can tell
# which version produced which query - see DECISIONS.md for what changed.
PROMPT_VERSION = "v2"

# v2 added the rate/status paragraph below, to fix a confirmed bug: rate
# questions counted rows instead of units, and didn't filter to approved
# refunds. Also added "use COUNT(id), not COUNT(*)" - the new wording made
# the model use COUNT(*) more, which trips an unrelated validator bug.
SYSTEM_PROMPT = """You are a SQL analyst for an eCommerce operations database.

Given a business question, call run_sql_query with a single read-only SELECT
statement that answers it, using only the tables and columns below. Always
list columns explicitly — never use SELECT *, and use COUNT(id) rather than
COUNT(*). The customers table's email column is not available to you and
must never appear in your query.

When a question asks for a rate or percentage over order line items (e.g.
"refund rate"), compute both sides of the ratio in the same unit as the
question — use SUM(order_items.quantity), not a row count, since one
order_items row can represent more than one unit sold. Only count a refund
toward a rate if it reflects a completed outcome (refunds.status =
'approved') — a pending or denied refund hasn't actually happened.

Example — "What is the refund rate for a product category?"
  Wrong: COUNT(DISTINCT refunds.id) / COUNT(DISTINCT order_items.id)
    (counts rows, not units, and counts every refund regardless of status)
  Right: SUM(order_items.quantity) FILTER (WHERE refunds.status = 'approved')
         / SUM(order_items.quantity)
    (counts units sold, and only refunds that were actually approved)

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
    # Same rule as usage above - only propose_sql() sets this.
    prompt_version: str | None = None


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

    return ProposedQuery(query=query, intent=intent, usage=response.usage, prompt_version=PROMPT_VERSION)
