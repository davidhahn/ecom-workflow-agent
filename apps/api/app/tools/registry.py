"""Formal tool registry: declares every tool the orchestrator can call, as
data rather than ad hoc inline dicts. Enumerable by design — Part 2's
tool-call trace UI and later multi-agent work loop over TOOLS.values()
rather than hardcoding tool names.

input_schema is reused directly from each tool's existing Anthropic-facing
spec (app.query.tool_spec, app.orchestrator.tool_specs) rather than
hand-copied, so there's exactly one source of truth for what Claude sees.
output_schema is generated from the real Pydantic response model for the
same reason — see the JSON-schema-vs-real-shape tests in tests/.

permission_required and requires_confirmation are declared here but not yet
checked against anything; enforcement is a later step.
"""

from dataclasses import dataclass
from typing import Any, Literal

from app.orchestrator.tool_specs import SEARCH_POLICY_TOOL
from app.query.schemas import SqlQueryResponse
from app.query.tool_spec import RUN_SQL_QUERY_TOOL
from app.rag.schemas import RagChunkResult

PermissionLevel = Literal["read_only", "write", "admin"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission_required: PermissionLevel
    error_behavior: str
    requires_confirmation: bool

    def anthropic_tool_def(self) -> dict[str, Any]:
        """The subset of this spec Anthropic's tool-calling API accepts."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


TOOLS: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        ToolSpec(
            name=RUN_SQL_QUERY_TOOL["name"],
            description=RUN_SQL_QUERY_TOOL["description"],
            input_schema=RUN_SQL_QUERY_TOOL["input_schema"],
            output_schema=SqlQueryResponse.model_json_schema(),
            permission_required="read_only",
            error_behavior=(
                "Never raises for expected failure modes: AST/permission/cost "
                "rejections and DB errors are caught and returned as a "
                "structured 'rejected'/'error' status with rejection_reason; "
                "every attempt (success, rejected, or error) is recorded to "
                "query_audit_log via record_attempt."
            ),
            requires_confirmation=False,
        ),
        ToolSpec(
            name=SEARCH_POLICY_TOOL["name"],
            description=SEARCH_POLICY_TOOL["description"],
            input_schema=SEARCH_POLICY_TOOL["input_schema"],
            output_schema={"type": "array", "items": RagChunkResult.model_json_schema()},
            permission_required="read_only",
            error_behavior=(
                "Does not catch exceptions itself; embedding or DB failures "
                "propagate to the enclosing request_log_span, which logs the "
                "failure to request_log and re-raises rather than returning "
                "a silent empty result."
            ),
            requires_confirmation=False,
        ),
    )
}


def anthropic_tool_defs() -> list[dict[str, Any]]:
    """Tool definitions in the shape Anthropic's `tools=` parameter expects,
    built from the registry so the orchestrator never hand-writes tool JSON."""
    return [spec.anthropic_tool_def() for spec in TOOLS.values()]
