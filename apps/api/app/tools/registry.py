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

exposed_to_analyze controls whether a tool is included in
anthropic_tool_defs(for_analyze=True) — the subset /query/analyze actually
advertises to Claude. Being in TOOLS (registered) and being wired into
analyze_service.py's tool-call loop (dispatched) are different things: a
tool the loop has no dispatch handler for must not be advertised there,
since an unhandled tool_use block leaves Claude's next turn without a
matching tool_result. New tools default to False until that integration
step is deliberately done.
"""

from dataclasses import dataclass
from typing import Any, Literal

from app.invoices.schemas import InvoiceConfirmResponse, InvoiceDraftResponse
from app.invoices.tool_spec import CONFIRM_VENDOR_INVOICE_TOOL, DRAFT_VENDOR_INVOICE_TOOL
from app.orchestrator.tool_specs import SEARCH_POLICY_TOOL
from app.query.schemas import SqlQueryResponse
from app.query.tool_spec import RUN_SQL_QUERY_TOOL
from app.rag.schemas import RagChunkResult
from app.shipments.schemas import ShipmentStatusResponse
from app.shipments.tool_spec import GET_SHIPMENT_STATUS_TOOL
from app.tickets.schemas import TicketConfirmResponse, TicketDraftResponse
from app.tickets.tool_spec import CONFIRM_SUPPORT_TICKET_TOOL, DRAFT_SUPPORT_TICKET_TOOL

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
    exposed_to_analyze: bool = False

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
            exposed_to_analyze=True,
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
            exposed_to_analyze=True,
        ),
        ToolSpec(
            name=GET_SHIPMENT_STATUS_TOOL["name"],
            description=GET_SHIPMENT_STATUS_TOOL["description"],
            input_schema=GET_SHIPMENT_STATUS_TOOL["input_schema"],
            output_schema=ShipmentStatusResponse.model_json_schema(),
            permission_required="read_only",
            error_behavior=(
                "Never raises for expected failure modes: an invalid status "
                "value or an unparseable date filter is caught and returned "
                "as a structured 'error' status with error_reason. No "
                "arbitrary SQL string is ever built from input — every "
                "filter is bound as a parameter via SQLAlchemy Core's query "
                "builder, executed through the same restricted "
                "ops_agent_readonly role as run_sql_query, capped at the "
                "same DEFAULT_LIMIT row cap."
            ),
            requires_confirmation=False,
        ),
        ToolSpec(
            name=DRAFT_SUPPORT_TICKET_TOOL["name"],
            description=DRAFT_SUPPORT_TICKET_TOOL["description"],
            input_schema=DRAFT_SUPPORT_TICKET_TOOL["input_schema"],
            output_schema=TicketDraftResponse.model_json_schema(),
            permission_required="read_only",
            error_behavior=(
                "Never raises for expected failure modes: extraction failure or "
                "an unresolvable customer/product reference is caught and "
                "returned as a structured 'could_not_process' status with "
                "reasoning, mirroring refund_evaluator's pattern exactly (see "
                "DECISIONS.md #16). Writes nothing to support_tickets — only to "
                "an in-memory draft store with a 10-minute TTL."
            ),
            requires_confirmation=True,
        ),
        ToolSpec(
            name=CONFIRM_SUPPORT_TICKET_TOOL["name"],
            description=CONFIRM_SUPPORT_TICKET_TOOL["description"],
            input_schema=CONFIRM_SUPPORT_TICKET_TOOL["input_schema"],
            output_schema=TicketConfirmResponse.model_json_schema(),
            permission_required="write",
            error_behavior=(
                "Never raises for expected failure modes: a missing or expired "
                "draft_id returns a structured 'error' status with error_reason, "
                "never a silent no-op. Re-confirming an already-confirmed "
                "draft_id is idempotent — returns the same ticket_id rather than "
                "inserting a duplicate row. Does raise (not caught) if "
                "draft_support_ticket's registry entry ever stops declaring "
                "requires_confirmation=True, since enforcing that gate is this "
                "tool's entire reason to exist."
            ),
            requires_confirmation=False,
        ),
        ToolSpec(
            name=DRAFT_VENDOR_INVOICE_TOOL["name"],
            description=DRAFT_VENDOR_INVOICE_TOOL["description"],
            input_schema=DRAFT_VENDOR_INVOICE_TOOL["input_schema"],
            output_schema=InvoiceDraftResponse.model_json_schema(),
            permission_required="read_only",
            error_behavior=(
                "Never raises for expected failure modes: an extraction failure "
                "(no tool_use returned, or a missing/invalid field) is caught and "
                "returned as a structured 'could_not_process' status with "
                "reasoning, mirroring draft_support_ticket's pattern exactly. "
                "Writes nothing to vendor_invoices — only to an in-memory draft "
                "store with a 10-minute TTL."
            ),
            requires_confirmation=True,
        ),
        ToolSpec(
            name=CONFIRM_VENDOR_INVOICE_TOOL["name"],
            description=CONFIRM_VENDOR_INVOICE_TOOL["description"],
            input_schema=CONFIRM_VENDOR_INVOICE_TOOL["input_schema"],
            output_schema=InvoiceConfirmResponse.model_json_schema(),
            permission_required="write",
            error_behavior=(
                "Never raises for expected failure modes: a missing or expired "
                "draft_id returns a structured 'error' status with error_reason, "
                "never a silent no-op. Re-confirming an already-confirmed "
                "draft_id is idempotent — returns the same invoice_id rather than "
                "inserting a duplicate row. The duplicate (vendor_name, "
                "invoice_number) check is re-run at confirm-time, not just "
                "draft-time, so a race between two drafts of the same invoice is "
                "still caught — vendor_invoices has a unique index on that pair, "
                "so a confirm-time duplicate returns a structured 'error' status "
                "(validation_status='duplicate') instead of attempting an insert "
                "that would violate the constraint. Does raise (not caught) if "
                "draft_vendor_invoice's registry entry ever stops declaring "
                "requires_confirmation=True, since enforcing that gate is this "
                "tool's entire reason to exist."
            ),
            requires_confirmation=False,
        ),
    )
}


def anthropic_tool_defs(*, for_analyze: bool = False) -> list[dict[str, Any]]:
    """Tool definitions in the shape Anthropic's `tools=` parameter expects,
    built from the registry so the orchestrator never hand-writes tool JSON.

    for_analyze=True restricts this to tools analyze_service.py's tool-call
    loop actually has a dispatch handler for (see exposed_to_analyze above);
    omit it to enumerate every registered tool regardless of integration
    status, e.g. for a tool-call trace UI or a registry contract test."""
    specs = TOOLS.values()
    if for_analyze:
        specs = [spec for spec in specs if spec.exposed_to_analyze]
    return [spec.anthropic_tool_def() for spec in specs]
