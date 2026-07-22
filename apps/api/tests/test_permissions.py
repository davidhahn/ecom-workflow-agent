"""Tests for permission enforcement v1 (app/permissions.py). Uses FastAPI's
TestClient against the real app (real Postgres, real registry) — exercises
the actual dependency wiring on each router, not a reimplementation of it.

The one case role-tier matching alone would get wrong: support_agent can
draft_support_ticket (permission_required="read_only") but not
confirm_support_ticket (permission_required="write") — same "ticket"
workflow, two different registry entries.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.permissions import DEFAULT_ROLE, ROLE_PERMISSIONS, resolve_role
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET

client = TestClient(app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})


def _headers(role: str | None) -> dict[str, str]:
    return {"X-Demo-Role": role} if role is not None else {}


def test_resolve_role_defaults_to_read_only_viewer_on_missing_or_invalid_header():
    assert resolve_role(None) == DEFAULT_ROLE
    assert resolve_role("") == DEFAULT_ROLE
    assert resolve_role("not_a_real_role") == DEFAULT_ROLE
    assert resolve_role("admin") == "admin"


def test_read_only_viewer_can_query_sql_but_not_confirm_tickets():
    sql_resp = client.post(
        "/query/sql", json={"question": "how many products exist?"}, headers=_headers("read_only_viewer")
    )
    assert sql_resp.status_code == 200

    confirm_resp = client.post(
        "/tickets/confirm", json={"draft_id": "irrelevant"}, headers=_headers("read_only_viewer")
    )
    assert confirm_resp.status_code == 403
    assert "read_only_viewer" in confirm_resp.json()["detail"]
    assert "write" in confirm_resp.json()["detail"]


def test_missing_header_behaves_identically_to_read_only_viewer():
    with_no_header = client.post("/tickets/confirm", json={"draft_id": "irrelevant"})
    with_explicit_role = client.post(
        "/tickets/confirm", json={"draft_id": "irrelevant"}, headers=_headers("read_only_viewer")
    )
    assert with_no_header.status_code == with_explicit_role.status_code == 403


def test_support_agent_can_draft_but_cannot_confirm_tickets():
    """The distinction that role-tier matching by string alone would get
    wrong: both endpoints are conceptually 'the ticket workflow', but
    draft_support_ticket is read_only and confirm_support_ticket is write."""
    draft_resp = client.post(
        "/tickets/draft",
        json={"request_text": "This is James O'Brien, billing question (perm test, unique phrasing)."},
        headers=_headers("support_agent"),
    )
    assert draft_resp.status_code == 200
    assert draft_resp.json()["status"] in ("drafted", "could_not_process")

    confirm_resp = client.post(
        "/tickets/confirm", json={"draft_id": "irrelevant"}, headers=_headers("support_agent")
    )
    assert confirm_resp.status_code == 403
    assert "support_agent" in confirm_resp.json()["detail"]


def test_manager_can_confirm_tickets():
    draft_resp = client.post(
        "/tickets/draft",
        json={"request_text": "This is James O'Brien, package never arrived (manager perm test)."},
        headers=_headers("manager"),
    )
    assert draft_resp.status_code == 200
    draft_id = draft_resp.json().get("draft_id")

    if draft_id is not None:
        confirm_resp = client.post("/tickets/confirm", json={"draft_id": draft_id}, headers=_headers("manager"))
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "created"
    else:
        # Extraction/resolution came back could_not_process for this run —
        # still proves the *permission* layer let a manager reach
        # confirm_ticket()'s own logic rather than blocking with a 403.
        confirm_resp = client.post("/tickets/confirm", json={"draft_id": "irrelevant"}, headers=_headers("manager"))
        assert confirm_resp.status_code != 403


def test_admin_can_access_everything_role_tier_allows():
    for method, path, body in [
        ("post", "/query/sql", {"question": "how many products exist?"}),
        ("post", "/query/rag", {"question": "what is the return window?"}),
        ("post", "/tickets/confirm", {"draft_id": "irrelevant"}),
    ]:
        resp = client.request(method, path, json=body, headers=_headers("admin"))
        assert resp.status_code != 403, f"{path} unexpectedly denied for admin"


def test_role_permissions_table_matches_task_spec():
    assert ROLE_PERMISSIONS == {
        "read_only_viewer": {"read_only"},
        "support_agent": {"read_only"},
        "manager": {"read_only", "write"},
        "admin": {"read_only", "write", "admin"},
    }
