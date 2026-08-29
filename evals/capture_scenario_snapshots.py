#!/usr/bin/env python3
"""Captures a real result for each curated landing-page scenario.

Runs every entry in apps/web/src/lib/scenarios.json against the real
/query/analyze or /refund/evaluate endpoint and writes the raw response
JSON to apps/web/src/lib/scenario-snapshots.json. The web app renders these
as pre-run results, so a visitor sees a real answer immediately instead of
an empty card and a wait.

Usage (from apps/api, so poetry deps and .env resolve like the pytest
suite):

    cd apps/api
    poetry run python ../../evals/capture_scenario_snapshots.py

Needs the seeded Postgres instance running and a working ANTHROPIC_API_KEY.
Safe to re-run: it always overwrites the whole file with a fresh capture.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
SCENARIOS_PATH = REPO_ROOT / "apps" / "web" / "src" / "lib" / "scenarios.json"
SNAPSHOTS_PATH = REPO_ROOT / "apps" / "web" / "src" / "lib" / "scenario-snapshots.json"

sys.path.insert(0, str(API_ROOT))

# Same reason as evals/run.py: all this traffic shares one IP, and the real
# per-hour rate limits are sized for a demo visitor, not a batch capture.
os.environ["EVAL_RATE_LIMIT_BYPASS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402


def main() -> None:
    scenarios = json.loads(SCENARIOS_PATH.read_text())
    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})
    role_headers = {"X-Demo-Role": "read_only_viewer"}

    results = {}
    for scenario in scenarios:
        if scenario["endpoint"] == "analyze":
            response = client.post(
                "/query/analyze",
                json={"question": scenario["input"], "bypass_cache": True},
                headers=role_headers,
            )
        else:
            response = client.post(
                "/refund/evaluate",
                json={"request_text": scenario["input"]},
                headers=role_headers,
            )

        response.raise_for_status()
        results[scenario["id"]] = response.json()
        print(f"captured {scenario['id']} ({scenario['endpoint']})")

    output = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    SNAPSHOTS_PATH.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {SNAPSHOTS_PATH}")


if __name__ == "__main__":
    main()
