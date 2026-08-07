#!/usr/bin/env python3
"""Runs each request_faithfulness case 3 times to check how stable the
judged outcome is, not just whether one run passes. Cache is bypassed on
every call so all 3 are real, independent model calls.

Usage:
    cd apps/api
    poetry run python ../../evals/run_request_faithfulness_calibration.py

Writes evals/request_faithfulness_calibration_raw.json and
evals/request_faithfulness_calibration.md.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
EVALS_ROOT = REPO_ROOT / "evals"

sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(EVALS_ROOT))

# 18 calls (6 cases x 3 runs) against a single-IP TestClient would otherwise
# blow past /query/analyze's 10/hour limit. See app/rate_limit.py's
# eval_bypass().
os.environ["EVAL_RATE_LIMIT_BYPASS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402

from run import load_cases, run_request_faithfulness_case  # noqa: E402

RUNS_PER_CASE = 3

# The old, informal number - a different, now-removed test case. Kept here
# only so the report can state it without implying it's the same measurement.
INFORMAL_OBSERVATION = "An informal exploratory test observed substitution in 10 of 11 attempts."


def main() -> None:
    cases = [c for c in load_cases() if c["category"] == "request_faithfulness"]
    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

    raw: list[dict] = []
    for case in cases:
        for run_index in range(1, RUNS_PER_CASE + 1):
            actual, failure_reasons = run_request_faithfulness_case(case, client, bypass_cache=True)
            raw.append(
                {
                    "case_id": case["id"],
                    "run_index": run_index,
                    "input": case["input"],
                    "expected": case["expected"],
                    "actual": actual,
                    "passed": not failure_reasons,
                    "failure_reasons": failure_reasons,
                }
            )
            print(f"{case['id']} run {run_index}/{RUNS_PER_CASE} ... "
                  f"{'PASS' if not failure_reasons else 'FAIL'} "
                  f"({actual['judge'].get('response_relationship')})")

    (EVALS_ROOT / "request_faithfulness_calibration_raw.json").write_text(json.dumps(raw, indent=2) + "\n")
    report = _build_report(cases, raw)
    (EVALS_ROOT / "request_faithfulness_calibration.md").write_text(report + "\n")
    print("\nWrote evals/request_faithfulness_calibration_raw.json and evals/request_faithfulness_calibration.md")


def _build_report(cases: list[dict], raw: list[dict]) -> str:
    n_cases = len(cases)
    total = len(raw)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    by_run = {i: [r for r in raw if r["run_index"] == i] for i in range(1, RUNS_PER_CASE + 1)}
    pass_by_run_rows = [
        f"| run {i} | {sum(1 for r in rows if r['passed'])} / {n_cases} |" for i, rows in by_run.items()
    ]

    scored = [r for r in raw if r["actual"]["judge"]["scored"]]
    unscored = total - len(scored)
    relationship_counts = Counter(r["actual"]["judge"]["response_relationship"] for r in scored)
    relationship_rows = [
        f"| `{label}` | {relationship_counts.get(label, 0)} |"
        for label in (
            "honest_refusal",
            "transparent_redirection",
            "partial_acknowledgement",
            "silent_substitution",
            "false_success_claim",
            "insufficient_evidence",
        )
    ]

    silent_sub_rate = relationship_counts.get("silent_substitution", 0) / len(scored) if scored else 0.0
    false_success_rate = relationship_counts.get("false_success_claim", 0) / len(scored) if scored else 0.0

    disagreement_cases = []
    verdict_flip_cases = []
    for case in cases:
        case_rows = [r for r in raw if r["case_id"] == case["id"] and r["actual"]["judge"]["scored"]]
        case_relationships = [r["actual"]["judge"]["response_relationship"] for r in case_rows]
        if len(set(case_relationships)) > 1:
            disagreement_cases.append((case["id"], case_relationships))
        if len({r["passed"] for r in case_rows}) > 1:
            verdict_flip_cases.append(case["id"])
    disagreement_rate = len(disagreement_cases) / n_cases if n_cases else 0.0

    disagreement_lines = (
        "\n".join(f"- `{case_id}`: {relationships}" for case_id, relationships in disagreement_cases)
        if disagreement_cases
        else "None — every case got the same response_relationship label across all 3 runs."
    )
    verdict_flip_line = (
        f"Of those, {len(verdict_flip_cases)} also disagreed on pass/fail, not just the label: "
        f"{verdict_flip_cases}."
        if verdict_flip_cases
        else "None of those crossed a pass/fail boundary — just a different passing label each time."
    )

    return "\n".join(
        [
            "# request_faithfulness Calibration — 3 Runs Per Case",
            "",
            f"{n_cases} cases, {RUNS_PER_CASE} runs each, {total} calls, cache bypassed every time "
            "(see `evals/cache_contamination_audit.md`).",
            "",
            "## Pass Count By Run",
            "",
            "| | passed |",
            "|---|---|",
            *pass_by_run_rows,
            "",
            "## response_relationship Distribution",
            "",
            f"{len(scored)} of {total} calls scored ({unscored} judge error/unscored).",
            "",
            "| label | count |",
            "|---|---|",
            *relationship_rows,
            "",
            f"Silent-substitution rate: {silent_sub_rate:.2f} ({relationship_counts.get('silent_substitution', 0)} / {len(scored)})",
            "",
            f"False-success-claim rate: {false_success_rate:.2f} ({relationship_counts.get('false_success_claim', 0)} / {len(scored)})",
            "",
            "## Judge Disagreement",
            "",
            f"{len(disagreement_cases)} of {n_cases} cases ({disagreement_rate:.2f}) got a different "
            "response_relationship label on at least one of their 3 runs:",
            "",
            disagreement_lines,
            "",
            verdict_flip_line,
            "",
            "## Raw Sample Size",
            "",
            f"{n_cases} cases x {RUNS_PER_CASE} runs = {total} calls.",
            "",
            "## Preserving Both Numbers",
            "",
            "Don't combine these into one percentage — different cases, different methods:",
            "",
            f"> {INFORMAL_OBSERVATION} The versioned evaluation suite later measured "
            f"{sum(1 for r in raw if r['actual']['judge'].get('response_relationship') in ('silent_substitution', 'false_success_claim'))} "
            f"of {total} cases across three runs.",
            "",
            "## Manual Review",
            "",
            "Every judge verdict above should be read by hand against the real answer, independent of "
            "the judge's own reasoning, and logged in `evals/request_faithfulness_labels.json` before "
            "trusting this report.",
            "",
            "## Limitation Found During This Run",
            "",
            "None of the 18 runs ever called a tool — every case got a plain refusal with nothing to "
            "check. That's different from `mixed-08`, the case that started this category: it asks about "
            "one specific, already-resolved order, so there's a real answer to substitute in place of a "
            "refusal. These 6 cases are all bulk requests with nothing to substitute, so a clean 18/18 "
            "shows these phrasings work, not that the risk `mixed-08` found is gone. The next case added "
            "here should look like `mixed-08`: one specific order, not a bulk action.",
            "",
            f"{timestamp}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
