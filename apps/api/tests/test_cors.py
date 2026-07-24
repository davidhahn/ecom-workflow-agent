"""Tests for the CORS origin restriction (app/main.py's ALLOWED_ORIGINS +
CORSMiddleware, added alongside the shared-secret proxy work — see
DECISIONS.md #23). This is a separate, independent layer from the
X-Internal-Proxy-Secret check covered in test_proxy_secret.py: CORS is
enforced by the browser and does nothing against a direct/non-browser
request, which is exactly what the secret check exists for.

Preflight (OPTIONS with Access-Control-Request-Method) is the clearest way
to prove the origin restriction actually works, not just that a value is
present in ALLOWED_ORIGINS: Starlette's CORSMiddleware answers a preflight
itself, before the request ever reaches ProxySecretMiddleware or a route,
returning 200 for an allowed origin and 400 for a disallowed one. A real
cross-origin browser POST with a JSON body (every write endpoint here)
triggers exactly this kind of preflight."""

from fastapi.testclient import TestClient

from app.main import ALLOWED_ORIGINS, app

client = TestClient(app)

PRODUCTION_ORIGIN = "https://ecom-workflow-agent-web.vercel.app"
DISALLOWED_ORIGIN = "https://evil.example.com"


def test_allowed_origins_is_the_real_production_domain_exactly():
    assert ALLOWED_ORIGINS == [PRODUCTION_ORIGIN]


def test_preflight_from_production_origin_is_allowed():
    resp = client.options(
        "/query/analyze",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == PRODUCTION_ORIGIN


def test_preflight_from_arbitrary_origin_is_rejected():
    resp = client.options(
        "/query/analyze",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_simple_response_only_carries_allow_origin_header_for_the_allowed_origin():
    """/health is exempt from the proxy-secret check (see app/proxy_secret.py),
    so this isolates CORS's own simple-request behavior: the
    Access-Control-Allow-Origin header is only ever mirrored back for an
    origin actually in ALLOWED_ORIGINS, never for an arbitrary one — the
    server still answers the disallowed-origin request (CORS is
    browser-enforced, not server-enforced, for non-preflight requests), it
    just omits the header a real browser would then refuse to expose the
    response for."""
    allowed = client.get("/health", headers={"Origin": PRODUCTION_ORIGIN})
    assert allowed.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN

    disallowed = client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})
    assert "access-control-allow-origin" not in disallowed.headers
