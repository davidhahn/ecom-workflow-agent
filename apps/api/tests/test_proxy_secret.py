"""Tests for the shared-secret check between apps/web/src/middleware.ts and this
backend (app/proxy_secret.py). Uses TestClient against the real app, same
as test_permissions.py — exercises the actual middleware wiring in
app/main.py, not a reimplementation of it.

Monkeypatches app.proxy_secret.INTERNAL_PROXY_SECRET to a known test-only
value rather than depending on whatever's configured in the real .env —
dispatch() re-reads the module attribute on every call (it's a plain
global lookup, not a value captured once into a closure), so the patch
takes effect for requests made after it's set."""

import app.proxy_secret as proxy_secret
from fastapi.testclient import TestClient

from app.main import app
from app.proxy_secret import HEADER_NAME

client = TestClient(app)

TEST_SECRET = "test-only-secret-value"


def test_missing_header_is_rejected(monkeypatch):
    monkeypatch.setattr(proxy_secret, "INTERNAL_PROXY_SECRET", TEST_SECRET)

    resp = client.get("/observability/requests")

    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"
    assert HEADER_NAME in resp.json()["message"]


def test_mismatched_header_is_rejected(monkeypatch):
    monkeypatch.setattr(proxy_secret, "INTERNAL_PROXY_SECRET", TEST_SECRET)

    resp = client.get("/observability/requests", headers={HEADER_NAME: "not-the-real-secret"})

    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"


def test_correct_header_succeeds(monkeypatch):
    monkeypatch.setattr(proxy_secret, "INTERNAL_PROXY_SECRET", TEST_SECRET)

    resp = client.get("/observability/requests", headers={HEADER_NAME: TEST_SECRET})

    assert resp.status_code == 200


def test_health_succeeds_without_header(monkeypatch):
    monkeypatch.setattr(proxy_secret, "INTERNAL_PROXY_SECRET", TEST_SECRET)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
