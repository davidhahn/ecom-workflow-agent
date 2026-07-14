"""Tests for the tool registry (app/tools/registry.py).

These deliberately go further than checking the registry dict has the right
keys: for each tool, a sample input built from input_schema is fed into the
*actual* handler function the orchestrator dispatches to, and the *actual*
response produced by the real underlying pipeline (real Postgres, real
embedding model) is validated against output_schema. A registry entry that
drifted from what the tool really accepts/returns should fail these.
"""

from dataclasses import fields
from unittest.mock import MagicMock, patch

import jsonschema

from app.orchestrator.analyze_service import (
    _run_run_sql_query_tool,
    _run_search_policy_tool,
    analyze,
)
from app.rag.service import query_rag
from app.tools.registry import TOOLS, ToolSpec, anthropic_tool_defs


def test_registry_is_enumerable_dict_of_toolspec():
    assert isinstance(TOOLS, dict)
    assert set(TOOLS) == {"run_sql_query", "search_policy"}
    for spec in TOOLS.values():
        assert isinstance(spec, ToolSpec)


def test_registry_entries_declare_all_required_fields():
    expected_fields = {
        "name",
        "description",
        "input_schema",
        "output_schema",
        "permission_required",
        "error_behavior",
        "requires_confirmation",
    }
    assert {f.name for f in fields(ToolSpec)} == expected_fields


def test_registry_entries_are_read_only_no_confirmation():
    for spec in TOOLS.values():
        assert spec.permission_required == "read_only"
        assert spec.requires_confirmation is False


def test_run_sql_query_input_schema_matches_real_handler():
    spec = TOOLS["run_sql_query"]
    sample_input = {
        "query": "SELECT id, category FROM products LIMIT 3",
        "intent": "tool registry contract check",
    }
    # Sample must actually validate against the declared input_schema.
    jsonschema.validate(sample_input, spec.input_schema)

    # And the exact function the orchestrator dispatches run_sql_query calls
    # to must accept exactly that shape and succeed against the real DB.
    executed = _run_run_sql_query_tool("what categories exist?", sample_input)
    assert executed.response.status == "success"


def test_run_sql_query_output_schema_matches_real_response():
    spec = TOOLS["run_sql_query"]
    executed = _run_run_sql_query_tool(
        "what categories exist?",
        {"query": "SELECT id, category FROM products LIMIT 3", "intent": "contract check"},
    )
    # This is exactly what analyze_service puts in the tool_result content.
    result_payload = executed.response.model_dump(mode="json")
    jsonschema.validate(result_payload, spec.output_schema)


def test_run_sql_query_output_schema_matches_rejected_response():
    """A rejected/error response must also validate, since output_schema
    describes the whole response union, not just the success case."""
    spec = TOOLS["run_sql_query"]
    executed = _run_run_sql_query_tool(
        "attempt a write",
        {"query": "UPDATE refunds SET status = 'approved'", "intent": "should be rejected"},
    )
    assert executed.response.status == "rejected"
    jsonschema.validate(executed.response.model_dump(mode="json"), spec.output_schema)


def test_search_policy_input_schema_matches_real_handler():
    spec = TOOLS["search_policy"]
    sample_input = {"query": "how long do I have to return a defective item?"}
    jsonschema.validate(sample_input, spec.input_schema)

    chunks = _run_search_policy_tool(sample_input)
    assert len(chunks) > 0


def test_search_policy_output_schema_matches_real_response():
    spec = TOOLS["search_policy"]
    chunks = query_rag("how long do I have to return a defective item?", k=3)
    # This is exactly what analyze_service puts in the tool_result content.
    result_payload = [c.model_dump() for c in chunks.chunks]
    jsonschema.validate(result_payload, spec.output_schema)


def test_orchestrator_builds_tool_list_from_registry_not_inline():
    """The actual payoff of the registry: /query/analyze's Claude call must
    receive exactly anthropic_tool_defs(), proving it reads from TOOLS rather
    than a parallel hand-written tools=[...] list it happens to ignore."""
    fake_usage = MagicMock(input_tokens=1, output_tokens=1)
    fake_text_block = MagicMock(type="text", text="fake answer, no rule citations here")
    fake_response = MagicMock(content=[fake_text_block], stop_reason="end_turn", usage=fake_usage)

    with patch("app.orchestrator.analyze_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = fake_response
        analyze("does this reach the registry?")

        _, kwargs = mock_anthropic_cls.return_value.messages.create.call_args
        assert kwargs["tools"] == anthropic_tool_defs()
        assert {t["name"] for t in kwargs["tools"]} == {"run_sql_query", "search_policy"}
