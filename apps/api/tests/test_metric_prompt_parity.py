"""Metric instructions at the model boundary; no live model or DB calls."""
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrator import analyze_service
from app.query import claude_client
from app.query.metric_instructions import SQL_METRIC_INSTRUCTIONS


class ModelBoundaryReached(Exception):
    pass


@pytest.mark.parametrize("module,invoke", [
    (analyze_service, lambda: analyze_service.analyze("Which products have the highest refund rate?", bypass_cache=True)),
    (claude_client, lambda: claude_client.propose_sql("Which products have the highest refund rate?")),
])
def test_both_model_paths_receive_the_metric_definition(module, invoke):
    with (
        patch.object(module, "build_schema_context", return_value="test schema"),
        patch.object(module, "new_client"),
        patch.object(module, "call_with_retry", side_effect=ModelBoundaryReached) as call,
        patch.object(analyze_service, "request_log_span", return_value=nullcontext(MagicMock())),
    ):
        with pytest.raises(ModelBoundaryReached):
            invoke()
    sent_prompt = call.call_args.kwargs["system"]
    assert SQL_METRIC_INSTRUCTIONS in sent_prompt
    assert "SUM(order_items.quantity)" in sent_prompt
    assert "refunds.status =\n'approved'" in sent_prompt


def test_analyze_does_not_reuse_a_pre_fix_cache_key():
    with (
        patch.object(analyze_service, "request_log_span", return_value=nullcontext(MagicMock())),
        patch.object(analyze_service, "cache_get", return_value=None) as cache,
        patch.object(analyze_service, "build_schema_context", return_value="test schema"),
        patch.object(analyze_service, "new_client"),
        patch.object(analyze_service, "call_with_retry", side_effect=ModelBoundaryReached),
    ):
        with pytest.raises(ModelBoundaryReached):
            analyze_service.analyze("Which products have the highest refund rate?")
    cache.assert_called_once_with("analyze", "v3:which products have the highest refund rate?")


def test_analyze_sql_audit_identifies_the_actual_prompt():
    with patch.object(analyze_service, "execute_proposed_query") as execute:
        analyze_service._run_run_sql_query_tool("refund rate", {"query": "SELECT id FROM products", "intent": "test"})
    assert execute.call_args.args[1].prompt_version == "analyze-v3"
