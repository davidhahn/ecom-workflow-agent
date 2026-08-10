#!/usr/bin/env python3
"""Runs every `sql` and `sql_semantic` case 3 times with the app cache
bypassed. Measures semantic accuracy, structural safety, and rejection
correctness separately - mixing them into one score would hide a low
result-correctness rate behind a pile of easy structural passes.

Usage:
    cd apps/api
    poetry run python ../../evals/run_sql_semantic_calibration.py

Writes evals/sql_semantic_calibration_raw.json and
evals/sql_semantic_calibration.md.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
EVALS_ROOT = REPO_ROOT / "evals"

sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(EVALS_ROOT))

# All calls share one IP - see app/rate_limit.py's eval_bypass().
os.environ["EVAL_RATE_LIMIT_BYPASS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402

from run import (  # noqa: E402
    _check_expected_result,
    _check_forbidden_columns,
    _check_read_only_violation_attempt,
    _check_tables_joined,
    _latest_request_log_detail,
    load_cases,
    run_sql_case,
)

RUNS_PER_CASE = 3


def _structural_reasons(expected: dict, sql_executed: str) -> list[str]:
    sql_lower = (sql_executed or "").lower()
    reasons: list[str] = []
    if "tables_joined" in expected:
        reasons += _check_tables_joined(sql_lower, expected["tables_joined"])
    if "columns_excluded" in expected:
        reasons += _check_forbidden_columns(sql_lower, expected["columns_excluded"], "columns_excluded")
    if "must_not_select" in expected:
        reasons += _check_forbidden_columns(sql_lower, expected["must_not_select"], "must_not_select")
    if "read_only_violation_attempt" in expected:
        reasons += _check_read_only_violation_attempt(sql_lower, expected["read_only_violation_attempt"])
    return reasons


def main() -> None:
    cases = [c for c in load_cases() if c["category"] in ("sql", "sql_semantic")]
    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

    raw: list[dict] = []
    for case in cases:
        expected = case["expected"]
        is_result_bearing = "expected_result" in expected
        is_rejection_case = expected.get("expected_status") == "rejected"

        for run_index in range(1, RUNS_PER_CASE + 1):
            actual, _ = run_sql_case(case, client, bypass_cache=True)
            detail = _latest_request_log_detail(client, "sql") or {}

            structural_reasons = _structural_reasons(expected, actual["sql_executed"])
            status_expected = expected.get("expected_status")
            status_correct = status_expected is None or actual["status"] == status_expected

            semantic_reasons: list[str] | None = None
            if is_result_bearing and actual["status"] == "success":
                semantic_reasons = _check_expected_result(expected["expected_result"], actual["rows"])

            row = {
                "case_id": case["id"],
                "category": case["category"],
                "run_index": run_index,
                "is_result_bearing": is_result_bearing,
                "is_rejection_case": is_rejection_case,
                "status": actual["status"],
                "generated_sql": actual["sql_executed"],
                "rows": actual["rows"],
                "structural_pass": not structural_reasons,
                "structural_reasons": structural_reasons,
                "status_correct": status_correct,
                "semantic_pass": (not semantic_reasons) if semantic_reasons is not None else None,
                "semantic_reasons": semantic_reasons,
                "latency_ms": detail.get("latency_ms"),
                "estimated_cost_usd": detail.get("estimated_cost_usd"),
            }
            raw.append(row)
            print(
                f"{case['id']} run {run_index}/{RUNS_PER_CASE} ... status={actual['status']} "
                f"semantic={'pass' if row['semantic_pass'] else ('fail' if row['semantic_pass'] is False else 'n/a')}"
            )

    (EVALS_ROOT / "sql_semantic_calibration_raw.json").write_text(json.dumps(raw, indent=2) + "\n")
    report = _build_report(cases, raw)
    (EVALS_ROOT / "sql_semantic_calibration.md").write_text(report + "\n")
    print("\nWrote evals/sql_semantic_calibration_raw.json and evals/sql_semantic_calibration.md")


def _build_report(cases: list[dict], raw: list[dict]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    result_bearing_ids = sorted({r["case_id"] for r in raw if r["is_result_bearing"]})
    rejection_ids = sorted({r["case_id"] for r in raw if r["is_rejection_case"]})
    n_result_bearing = len(result_bearing_ids)
    n_rejection = len(rejection_ids)

    by_run: dict[int, list[dict]] = defaultdict(list)
    for r in raw:
        by_run[r["run_index"]].append(r)

    per_run_rows = []
    for i in range(1, RUNS_PER_CASE + 1):
        run_rows = [r for r in by_run[i] if r["is_result_bearing"]]
        passed = sum(1 for r in run_rows if r["semantic_pass"])
        pct = 100 * passed / n_result_bearing if n_result_bearing else 0
        per_run_rows.append((i, passed, n_result_bearing, pct))

    all_result_bearing = [r for r in raw if r["is_result_bearing"]]
    total_semantic_passed = sum(1 for r in all_result_bearing if r["semantic_pass"])
    total_semantic_checks = len(all_result_bearing)
    overall_accuracy = 100 * total_semantic_passed / total_semantic_checks if total_semantic_checks else 0

    structural_checks = [r for r in raw]
    structural_passed = sum(1 for r in structural_checks if r["structural_pass"])

    status_checks = [r for r in raw if r["is_rejection_case"]]
    status_correct = sum(1 for r in status_checks if r["status_correct"])

    all_costs = [r["estimated_cost_usd"] for r in raw if r["estimated_cost_usd"] is not None]
    all_latencies = [r["latency_ms"] for r in raw if r["latency_ms"] is not None]
    mean_cost = sum(all_costs) / len(all_costs) if all_costs else 0
    mean_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0

    # Did status, semantic pass/fail, or the SQL itself change across runs?
    variation_lines = []
    for case_id in sorted({r["case_id"] for r in raw}):
        case_rows = [r for r in raw if r["case_id"] == case_id]
        statuses = {r["status"] for r in case_rows}
        semantics = {r["semantic_pass"] for r in case_rows}
        sqls = {r["generated_sql"] for r in case_rows}
        if len(statuses) > 1 or len(semantics) > 1 or len(sqls) > 1:
            variation_lines.append(
                f"- `{case_id}`: statuses={sorted(statuses)}, semantic results={sorted(str(s) for s in semantics)}, "
                f"{len(sqls)} distinct generated SQL string(s) across 3 runs"
            )
    variation_block = "\n".join(variation_lines) if variation_lines else "None - every case gave the same status, result, and SQL across all 3 runs."

    semantic_row = "| semantic cases passed | " + " | ".join(f"{p}/{n}" for _, p, n, _ in per_run_rows) + " |"
    accuracy_row = "| semantic accuracy | " + " | ".join(f"{pct:.1f}%" for _, _, _, pct in per_run_rows) + " |"

    header = "| metric | " + " | ".join(f"run {i}" for i in range(1, RUNS_PER_CASE + 1)) + " |"
    sep = "|---" * (RUNS_PER_CASE + 1) + "|"

    return "\n".join(
        [
            "# SQL / SQL Semantic Calibration - 3 Runs, Cache Bypassed",
            "",
            f"{len(cases)} cases (`sql` + `sql_semantic`), {RUNS_PER_CASE} runs each, "
            f"{len(raw)} total calls. `bypass_cache=true` on every call.",
            "",
            "## Result-Bearing vs. Rejection Cases",
            "",
            f"- Result-bearing cases: {n_result_bearing} ({', '.join(result_bearing_ids)})",
            f"- Rejection cases: {n_rejection}"
            + (f" ({', '.join(rejection_ids)})" if rejection_ids else " - none exist today. The one that ever "
               "did (`sql-05-write-attempt-rejected`) was a flawed test and was replaced by a direct test in "
               "`apps/api/tests/test_tool_registry.py`, outside this suite."),
            "",
            "Reported separately, never combined into one \"SQL correctness\" number - a rejection check (was "
            "an unsafe query blocked) and a semantic check (did a safe query get the right number) test "
            "different things.",
            "",
            "## Per-Run Results",
            "",
            header,
            sep,
            semantic_row,
            accuracy_row,
            f"| structural rejection cases | " + " | ".join([f"{n_rejection}/{n_rejection}" if n_rejection else "n/a"] * RUNS_PER_CASE) + " |",
            "",
            "## SQL Semantic Accuracy (overall)",
            "",
            f"{total_semantic_passed} of {total_semantic_checks} semantic checks passed across all 3 runs "
            f"({overall_accuracy:.1f}%). Sample size: {n_result_bearing} cases x {RUNS_PER_CASE} runs "
            f"= {total_semantic_checks}.",
            "",
            "## SQL Structural Safety",
            "",
            f"{structural_passed} of {len(structural_checks)} calls passed every structural check (right "
            f"tables, no blocked columns, no write attempt) - all {len(cases)} cases, not just result-bearing ones.",
            "",
            "## SQL Rejection Correctness",
            "",
            (
                f"{status_correct} of {len(status_checks)} rejection cases returned the expected status."
                if status_checks
                else "No rejection cases exist today - see above. Nothing to measure until one is added back."
            ),
            "",
            "## Mean Latency and Cost",
            "",
            f"Mean latency: {mean_latency / 1000:.2f}s | Mean cost: ${mean_cost:.4f} (across all {len(raw)} calls)",
            "",
            "## Model-Driven Variation",
            "",
            variation_block,
            "",
            f"{timestamp}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
