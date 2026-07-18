"""Permission enforcement v1: a header-based demo role, not real
authentication. One FastAPI dependency, `require_permission(tool_name,
request_type)`, reused on every tool-backed endpoint — not a
per-endpoint-reimplemented check.

The role is read from the X-Demo-Role request header. Missing or invalid
values fail closed to the least-privileged role (read_only_viewer), never
to open access — a request that forgets the header should get *less*
access than one that sends a bad value on purpose, not more.
"""

from typing import Any

from fastapi import Header, HTTPException, Request

from app.observability.logger import log_request
from app.tools.registry import TOOLS

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "read_only_viewer": {"read_only"},
    "support_agent": {"read_only"},  # can draft tickets (read_only), not confirm (write)
    "manager": {"read_only", "write"},
    "admin": {"read_only", "write", "admin"},
}

DEFAULT_ROLE = "read_only_viewer"


def resolve_role(x_demo_role: str | None) -> str:
    """Missing/invalid header -> DEFAULT_ROLE (fail closed), not an error."""
    if x_demo_role in ROLE_PERMISSIONS:
        return x_demo_role
    return DEFAULT_ROLE


def require_permission(tool_name: str, request_type: str):
    """Dependency factory: Depends(require_permission("run_sql_query", "sql")).

    Looks up TOOLS[tool_name].permission_required from the registry — the
    same single source of truth error_behavior/requires_confirmation already
    come from — and checks it against the caller's role. This is what makes
    the support_agent draft/confirm distinction correct: draft_support_ticket
    and confirm_support_ticket are looked up as two different tool_names with
    two different declared permission_required values ("read_only" vs
    "write"), not matched by any shared string/endpoint-name heuristic that
    could conflate the two "ticket" endpoints.
    """
    tool_permission = TOOLS[tool_name].permission_required

    async def dependency(
        request: Request,
        x_demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
    ) -> str:
        role = resolve_role(x_demo_role)
        if tool_permission in ROLE_PERMISSIONS[role]:
            return role

        message = f"role '{role}' cannot access tool requiring '{tool_permission}' permission"
        body_bytes = await request.body()
        input_text = body_bytes.decode("utf-8", errors="replace") if body_bytes else ""
        output: dict[str, Any] = {
            "error": "permission_denied",
            "message": message,
            "role": role,
            "required_permission": tool_permission,
        }
        # Denials still produce a request_log row like any other request —
        # nothing about this path runs through the request_log_span the
        # route handler would normally open (the dependency short-circuits
        # before the handler body ever runs), so it's logged directly here.
        log_request(request_type=request_type, input_text=input_text, output=output, latency_ms=0)

        raise HTTPException(status_code=403, detail=message)

    return dependency
