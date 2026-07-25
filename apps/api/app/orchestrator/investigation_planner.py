"""Planner step of the investigation pipeline (Planner -> Data Analyst ->
[Report Writer, not built yet]). A single, non-looping Claude tool-call
request — same pattern as app/query/claude_client.py's propose_sql(): one
system prompt, one forced tool call, no back-and-forth. The Planner never
touches the database or the RAG index itself; it only decides what should
be checked and how. Executing the plan is the Data Analyst's job
(app/orchestrator/data_analyst.py), reusing run_sql_query/query_rag
directly rather than this module reimplementing either.
"""

import os
from dataclasses import dataclass
from typing import Any, Literal

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL

load_dotenv()

Method = Literal["sql", "rag"]

PROPOSE_INVESTIGATION_PLAN_TOOL = {
    "name": "propose_investigation_plan",
    "description": (
        "Propose a structured plan for investigating a business question: a "
        "list of independent signals to check, each with a short name, the "
        "method to check it with, and a one-sentence intent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "signals": {
                "type": "array",
                "description": "The signals to check, in the order they should be checked.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "Short, lowercase, snake_case identifier for this signal, "
                                "e.g. 'revenue', 'traffic_conversion', 'refunds', "
                                "'campaign_context'."
                            ),
                        },
                        "method": {
                            "type": "string",
                            "enum": ["sql", "rag"],
                            "description": (
                                "'sql' to query the live ops database (orders, "
                                "order_items, web_analytics, refunds, ...). 'rag' to "
                                "search company policy and notes documents for "
                                "context (refund policy, shipping policy, campaign "
                                "launch notes, ...)."
                            ),
                        },
                        "intent": {
                            "type": "string",
                            "description": (
                                "One sentence describing exactly what this signal "
                                "checks and why it's relevant to the question. This "
                                "is handed to the SQL analyst or the policy search "
                                "verbatim as the thing to investigate, so it must be "
                                "self-contained, not a fragment that only makes "
                                "sense next to the other signals."
                            ),
                        },
                    },
                    "required": ["name", "method", "intent"],
                },
            },
        },
        "required": ["signals"],
    },
}

SYSTEM_PROMPT = """You are the planning step of an ops-investigation \
pipeline. Given a business question, propose a short list of independent \
signals worth checking before anyone answers it — you are not answering \
the question yourself, only deciding what evidence should be gathered.

Two methods are available to check a signal:
- sql: a live query against the ops database (orders, order_items, \
customers, products, refunds, support_tickets, web_analytics, campaigns).
- rag: a semantic search over company policy and notes documents (refund \
policy, shipping policy, support playbook, campaign launch notes).

For a question about a metric changing (a drop or spike in revenue, \
traffic, refunds, or similar), a good plan almost always includes:
1. The metric itself, computed directly (sql) — don't take the premise of \
the question on faith, verify the actual numbers.
2. A related leading-indicator signal if one exists (sql) — e.g. session/ \
conversion data alongside a revenue question, since revenue is downstream \
of traffic and conversion.
3. An elimination check (sql) — the obvious alternative explanation \
(e.g. a refund spike) checked and, if it turns out flat or unremarkable, \
ruled out rather than assumed. Investigating a metric change means \
checking the plausible causes, not just narrating the drop.
4. Business/campaign context (rag) — anything in company notes or policy \
documents (e.g. a marketing campaign that recently started or ended) that \
could plausibly explain a change of this kind.

Each signal's intent must be a single, self-contained sentence — it gets \
handed directly to whichever tool executes it, without the rest of the \
plan alongside it for context.
"""


@dataclass
class InvestigationSignal:
    name: str
    method: Method
    intent: str


@dataclass
class InvestigationPlan:
    signals: list[InvestigationSignal]
    usage: Any = None


class InvestigationPlanError(Exception):
    pass


def plan_investigation(question: str) -> InvestigationPlan:
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[PROPOSE_INVESTIGATION_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "propose_investigation_plan"},
        messages=[{"role": "user", "content": question}],
    )

    tool_use = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use is None:
        raise InvestigationPlanError(
            f"Claude did not return a propose_investigation_plan tool call "
            f"(stop_reason={response.stop_reason})"
        )

    raw_signals = tool_use.input.get("signals")
    if not raw_signals:
        raise InvestigationPlanError(
            f"propose_investigation_plan tool call had no signals: {tool_use.input}"
        )

    try:
        signals = [
            InvestigationSignal(name=s["name"], method=s["method"], intent=s["intent"])
            for s in raw_signals
        ]
    except KeyError as e:
        raise InvestigationPlanError(
            f"propose_investigation_plan signal missing required field: {e}"
        ) from e

    return InvestigationPlan(signals=signals, usage=response.usage)
