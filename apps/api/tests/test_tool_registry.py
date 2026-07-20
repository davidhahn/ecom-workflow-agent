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
from app.shipments.service import get_shipment_status
from app.tools.registry import TOOLS, ToolSpec, anthropic_tool_defs


def test_registry_is_enumerable_dict_of_toolspec():
    assert isinstance(TOOLS, dict)
    assert set(TOOLS) == {
        "run_sql_query",
        "search_policy",
        "get_shipment_status",
        "draft_support_ticket",
        "confirm_support_ticket",
        "draft_vendor_invoice",
        "confirm_vendor_invoice",
    }
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
        "exposed_to_analyze",
    }
    assert {f.name for f in fields(ToolSpec)} == expected_fields


def test_registry_permission_and_confirmation_flags_are_correct_per_tool():
    """Was 'every tool is read_only/no-confirmation' until confirm_support_ticket
    (the first real write) and draft_support_ticket (the first
    requires_confirmation=True) were registered — this asserts the actual
    per-tool split instead of a blanket rule that's no longer true."""
    write_tools = {"confirm_support_ticket", "confirm_vendor_invoice"}
    read_only_tools = set(TOOLS) - write_tools

    for name in read_only_tools:
        assert TOOLS[name].permission_required == "read_only"
    for name in write_tools:
        assert TOOLS[name].permission_required == "write"

    confirmation_required_tools = {"draft_support_ticket", "draft_vendor_invoice"}
    for name in TOOLS:
        expected = name in confirmation_required_tools
        assert TOOLS[name].requires_confirmation is expected


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
    receive exactly anthropic_tool_defs(for_analyze=True), proving it reads
    from TOOLS rather than a parallel hand-written tools=[...] list it
    happens to ignore."""
    fake_usage = MagicMock(input_tokens=1, output_tokens=1)
    fake_text_block = MagicMock(type="text", text="fake answer, no rule citations here")
    fake_response = MagicMock(content=[fake_text_block], stop_reason="end_turn", usage=fake_usage)

    with patch("app.orchestrator.analyze_service.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = fake_response
        analyze("does this reach the registry, unique phrasing for cache-miss safety?")

        _, kwargs = mock_anthropic_cls.return_value.messages.create.call_args
        assert kwargs["tools"] == anthropic_tool_defs(for_analyze=True)
        assert {t["name"] for t in kwargs["tools"]} == {"run_sql_query", "search_policy"}


def test_get_shipment_status_is_registered_but_not_exposed_to_analyze():
    """get_shipment_status is registered (the task's actual ask) but must
    not be advertised to /query/analyze's Claude call yet, since
    analyze_service.py's tool-loop has no dispatch handler for it — an
    unhandled tool_use block would leave the next turn without a matching
    tool_result. Wiring that in is a deliberate later step, not a side
    effect of registering the tool."""
    assert TOOLS["get_shipment_status"].exposed_to_analyze is False
    assert "get_shipment_status" not in {
        t["name"] for t in anthropic_tool_defs(for_analyze=True)
    }
    assert "get_shipment_status" in {t["name"] for t in anthropic_tool_defs()}


def test_get_shipment_status_input_schema_matches_real_handler():
    spec = TOOLS["get_shipment_status"]
    sample_input = {"product_name": "Stainless Steel Water Bottle", "status": "delayed"}
    jsonschema.validate(sample_input, spec.input_schema)

    result = get_shipment_status(**sample_input)
    assert result.status == "success"
    assert result.row_count > 0


def test_get_shipment_status_output_schema_matches_real_response():
    spec = TOOLS["get_shipment_status"]
    result = get_shipment_status(product_name="Stainless Steel Water Bottle", status="delayed")
    jsonschema.validate(result.model_dump(mode="json"), spec.output_schema)


def test_get_shipment_status_output_schema_matches_error_response():
    """error is part of the same response union output_schema describes,
    not just the success case."""
    spec = TOOLS["get_shipment_status"]
    result = get_shipment_status(status="not_a_real_status")
    assert result.status == "error"
    jsonschema.validate(result.model_dump(mode="json"), spec.output_schema)


def test_invoice_tools_are_registered_but_not_exposed_to_analyze():
    """draft_vendor_invoice / confirm_vendor_invoice are registered (the
    task's actual ask) but must not be advertised to /query/analyze's Claude
    call in this pass — analyze_service.py's tool-loop has no dispatch
    handler for either, same reasoning as get_shipment_status above."""
    for name in ("draft_vendor_invoice", "confirm_vendor_invoice"):
        assert TOOLS[name].exposed_to_analyze is False
        assert name not in {t["name"] for t in anthropic_tool_defs(for_analyze=True)}
        assert name in {t["name"] for t in anthropic_tool_defs()}
