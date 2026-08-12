"""Tests for the observability API additions: GET /observability/requests/{id}
for single-row detail (including tool_calls), and that the existing list
endpoint stays summary-only (no tool_calls key at all, not just an empty
one) rather than bloating every row of a list response with a full trace
payload."""

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.main import app
from app.orchestrator.analyze_service import analyze
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET

client = TestClient(app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

_RUN_ID = uuid.uuid4().hex[:8]


def _fake_final_answer_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    usage = MagicMock(input_tokens=1, output_tokens=1)
    return MagicMock(content=[block], stop_reason="end_turn", usage=usage)


def _analyze_row_id(question: str) -> uuid.UUID:
    with SessionLocal() as session:
        row = session.execute(
            select(RequestLog)
            .where(RequestLog.request_type == "analyze")
            .where(RequestLog.input == question)
            .order_by(RequestLog.created_at.desc())
        ).scalars().first()
    assert row is not None
    return row.id


def test_get_request_endpoint_returns_tool_calls_for_analyze_row():
    question = f"observability detail endpoint test, answered directly ({_RUN_ID})"
    with patch("app.llm_retry.anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = _fake_final_answer_response(
            "Direct answer, no tools needed for this one."
        )
        analyze(question)

    request_id = _analyze_row_id(question)

    resp = client.get(f"/observability/requests/{request_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(request_id)
    assert body["request_type"] == "analyze"
    # Answered directly, no tool_use in the fake response — an empty array,
    # not null, since this request_type always logs a trace.
    assert body["tool_calls"] == []


def test_get_request_endpoint_404_for_unknown_id():
    resp = client.get(f"/observability/requests/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_list_requests_endpoint_omits_tool_calls_field():
    """The list endpoint's response_model (RequestLogRow) has no tool_calls
    field at all — asserts the key is genuinely absent from the serialized
    JSON, not just null, proving the list stays summary-only rather than
    shipping a trace payload on every row."""
    resp = client.get("/observability/requests", params={"request_type": "analyze", "limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["requests"]) >= 1
    for row in body["requests"]:
        assert "tool_calls" not in row
