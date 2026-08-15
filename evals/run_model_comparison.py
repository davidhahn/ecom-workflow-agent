#!/usr/bin/env python3
"""Two-model comparison: the current app model against a cheaper one, on
the full applicable suite, three runs each, cache bypassed throughout.

"Applicable" means every category that actually calls a model.
refund_evaluator, groundedness, and topic_coverage are pure functions with
no model dependency at all, so a model swap can't change their result.
They're left out on purpose, not by oversight.

Only ANTHROPIC_MODEL changes between the two arms. The judge always runs
on JUDGE_MODEL (app/orchestrator/judge_client.py), fixed independently of
which model is under test, same prompt versions, same RELEVANCE_THRESHOLD,
same retry settings, same cases.json, same seeded database, same scoring
code in run.py. One variable moves.

request_log's own estimated_cost_usd column assumes Sonnet pricing no
matter which model actually ran (app/observability/pricing.py has no
model field to look a rate up by). This script prices each run itself,
from the real per-run token counts, using
app/observability/pricing.estimate_cost_usd_for_model().

Usage:
    cd apps/api
    poetry run python ../../evals/run_model_comparison.py

Writes evals/model_comparison_raw.json and evals/model_comparison.md.
"""

import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
EVALS_ROOT = REPO_ROOT / "evals"

sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(EVALS_ROOT))

os.environ["EVAL_RATE_LIMIT_BYPASS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.observability.pricing import estimate_cost_usd_for_model  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402
from app.query.claude_client import DEFAULT_MODEL as CURRENT_MODEL  # noqa: E402

from run import (  # noqa: E402
    NOT_RUNNABLE_CASE_IDS,
    load_cases,
    run_case,
)

RUNS_PER_MODEL = 3
CHEAP_MODEL = "claude-haiku-4-5-20251001"
MODELS = [("current", CURRENT_MODEL), ("cheap", CHEAP_MODEL)]

# Every category with a real model dependency somewhere in its path.
# refund_evaluator, groundedness, and topic_coverage wrap pure functions -
# no model call anywhere in them, so they're excluded rather than run and
# shown as an identical, uninformative row.
TARGET_CATEGORIES = {
    "sql",
    "sql_semantic",
    "rag",
    "permission",
    "mixed",
    "prompt_injection",
    "request_faithfulness",
    "resilience",
}

# Below this n, this project's own convention (evals/run.py's report) already
# treats a percentage as noise rather than a trend. Applied the same way here.
MIN_N_FOR_PERCENTAGE = 8


def run_one(case: dict, client: TestClient, model: str) -> dict:
    result = run_case(case, client, bypass_cache=True)
    detail = result.request_log_detail or {}
    input_tokens = detail.get("input_tokens")
    output_tokens = detail.get("output_tokens")
    cost = estimate_cost_usd_for_model(model, input_tokens, output_tokens)
    tool_call_count = None
    if detail.get("tool_calls") is not None:
        tool_call_count = len(detail["tool_calls"])
    return {
        "case_id": case["id"],
        "category": case["category"],
        "passed": result.passed,
        "latency_ms": result.latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "tool_call_count": tool_call_count,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=[label for label, _ in MODELS],
        default=None,
        help="Re-run only one model arm and merge into the existing "
        "evals/model_comparison_raw.json, instead of re-running both. For "
        "picking up after a run that failed partway through one arm, "
        "without re-paying for the arm that already completed cleanly.",
    )
    args = parser.parse_args()

    cases = [
        c
        for c in load_cases()
        if c["category"] in TARGET_CATEGORIES and c["id"] not in NOT_RUNNABLE_CASE_IDS
    ]
    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

    models_to_run = [(label, model_id) for label, model_id in MODELS if args.only in (None, label)]

    kept: list[dict] = []
    if args.only:
        existing = json.loads((EVALS_ROOT / "model_comparison_raw.json").read_text())
        kept = [r for r in existing if r["model_label"] != args.only]
        print(f"Keeping {len(kept)} existing rows, re-running the '{args.only}' arm.")

    raw: list[dict] = list(kept)
    for model_label, model_id in models_to_run:
        os.environ["ANTHROPIC_MODEL"] = model_id
        print(f"\n=== {model_label} ({model_id}) ===")
        for run_index in range(1, RUNS_PER_MODEL + 1):
            for case in cases:
                record = run_one(case, client, model_id)
                record["model_label"] = model_label
                record["model_id"] = model_id
                record["run_index"] = run_index
                raw.append(record)
                print(f"  run {run_index}/{RUNS_PER_MODEL}  {case['id']:45s} {'PASS' if record['passed'] else 'FAIL'}")

    (EVALS_ROOT / "model_comparison_raw.json").write_text(json.dumps(raw, indent=2, default=str) + "\n")
    print("\nWrote evals/model_comparison_raw.json")

    report = build_report(raw, cases)
    (EVALS_ROOT / "model_comparison.md").write_text(report + "\n")
    print("Wrote evals/model_comparison.md")


def _p50(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def build_report(raw: list[dict], cases: list[dict]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    categories = sorted({c["category"] for c in cases})
    n_by_category = {cat: len([c for c in cases if c["category"] == cat]) for cat in categories}

    by_model_category: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in raw:
        by_model_category[(r["model_label"], r["category"])].append(r)

    def per_run_pass_rate(rows: list[dict], n: int) -> list[int]:
        by_run: dict[int, list[dict]] = defaultdict(list)
        for r in rows:
            by_run[r["run_index"]].append(r)
        rates = []
        for run_index in sorted(by_run):
            passed = sum(1 for r in by_run[run_index] if r["passed"])
            rates.append(round(100 * passed / n) if n else 0)
        return rates

    def fmt_dollars(value: float | None) -> str:
        return f"${value:.4f}" if value is not None else "n/a (mocked, no tokens)"

    def fmt_seconds(value: float | None) -> str:
        return f"{value:.1f}s" if value is not None else "n/a"

    lines = [
        "# Model Comparison: Current vs. Cheap",
        "",
        f"`{CURRENT_MODEL}` (current) against `{CHEAP_MODEL}` (cheap). "
        f"{RUNS_PER_MODEL} runs each, cache bypassed on every call, against the same cases.json, "
        "the same seeded database, the same prompts, the same RELEVANCE_THRESHOLD, the same retry "
        "settings, and the same scoring code in evals/run.py. The judge stayed on "
        "JUDGE_MODEL throughout, for both arms - only the app model under test changed. "
        "Raw per-run data lives in `evals/model_comparison_raw.json`.",
        "",
        f"refund_evaluator, groundedness, and topic_coverage aren't here. Nothing in any of "
        "them calls a model, so a model swap has nothing to change.",
        "",
        "## Per-Category Comparison",
        "",
        "| category | n | current quality | cheap quality | current p50 | cheap p50 "
        "| current cost | cheap cost |",
        "|---|---|---|---|---|---|---|---|",
    ]

    detail_sections = []

    for cat in categories:
        n = n_by_category[cat]
        cur_rows = by_model_category[("current", cat)]
        cheap_rows = by_model_category[("cheap", cat)]

        cur_rates = per_run_pass_rate(cur_rows, n)
        cheap_rates = per_run_pass_rate(cheap_rows, n)

        if n >= MIN_N_FOR_PERCENTAGE:
            cur_quality = f"{_mean(cur_rates):.0f}% (runs: {'/'.join(str(r) for r in cur_rates)})"
            cheap_quality = f"{_mean(cheap_rates):.0f}% (runs: {'/'.join(str(r) for r in cheap_rates)})"
        else:
            cur_quality = f"{sum(1 for r in cur_rows if r['passed'])}/{len(cur_rows)} (n={n}, see detail)"
            cheap_quality = f"{sum(1 for r in cheap_rows if r['passed'])}/{len(cheap_rows)} (n={n}, see detail)"

        cur_latencies = [r["latency_ms"] / 1000 for r in cur_rows if r["latency_ms"] is not None]
        cheap_latencies = [r["latency_ms"] / 1000 for r in cheap_rows if r["latency_ms"] is not None]
        cur_p50 = _p50(cur_latencies)
        cheap_p50 = _p50(cheap_latencies)

        cur_costs = [r["cost_usd"] for r in cur_rows if r["cost_usd"] is not None]
        cheap_costs = [r["cost_usd"] for r in cheap_rows if r["cost_usd"] is not None]
        cur_cost = _mean(cur_costs)
        cheap_cost = _mean(cheap_costs)

        lines.append(
            f"| {cat} | {n} | {cur_quality} | {cheap_quality} | "
            f"{fmt_seconds(cur_p50)} | {fmt_seconds(cheap_p50)} | "
            f"{fmt_dollars(cur_cost)} | {fmt_dollars(cheap_cost)} |"
        )

        if n < MIN_N_FOR_PERCENTAGE:
            case_ids = sorted({c["id"] for c in cases if c["category"] == cat})
            section = [f"### {cat} (n={n}, individual runs)", ""]
            for case_id in case_ids:
                cur_case_rows = [r for r in cur_rows if r["case_id"] == case_id]
                cheap_case_rows = [r for r in cheap_rows if r["case_id"] == case_id]
                cur_outcomes = "/".join("P" if r["passed"] else "F" for r in sorted(cur_case_rows, key=lambda r: r["run_index"]))
                cheap_outcomes = "/".join("P" if r["passed"] else "F" for r in sorted(cheap_case_rows, key=lambda r: r["run_index"]))
                section.append(f"- `{case_id}`: current {cur_outcomes}, cheap {cheap_outcomes}")
            section.append("")
            detail_sections.append("\n".join(section))

    mixed_cur = by_model_category[("current", "mixed")]
    mixed_cheap = by_model_category[("cheap", "mixed")]
    if mixed_cur or mixed_cheap:
        cur_tool_counts = [r["tool_call_count"] for r in mixed_cur if r["tool_call_count"] is not None]
        cheap_tool_counts = [r["tool_call_count"] for r in mixed_cheap if r["tool_call_count"] is not None]
        cur_mean_calls = _mean(cur_tool_counts)
        cheap_mean_calls = _mean(cheap_tool_counts)
        detail_sections.append(
            "### mixed: mean tool-call count\n\n"
            f"current: {cur_mean_calls:.2f} calls per case. "
            f"cheap: {cheap_mean_calls:.2f} calls per case.\n"
            if cur_mean_calls is not None and cheap_mean_calls is not None
            else "### mixed: mean tool-call count\n\nNo tool-call data recorded for one or both arms.\n"
        )

    lines += ["", "## Small-Category Detail", ""]
    lines += detail_sections if detail_sections else ["Every category met the n >= 8 threshold above."]

    lines += [
        "",
        "## Reading the cost numbers",
        "",
        "Cost here comes from real input and output token counts for each run, priced with "
        "app/observability/pricing.estimate_cost_usd_for_model(). request_log's own "
        "estimated_cost_usd column is not used for this table - it assumes Sonnet pricing "
        "regardless of which model actually answered.",
        "",
        f"Sonnet rate: $3.00 / $15.00 per million input/output tokens. "
        f"Haiku rate: $1.00 / $5.00 per million input/output tokens, entered by hand and worth "
        "checking against Anthropic's current pricing page before trusting it for a real budget "
        "decision.",
        "",
        f"Generated {timestamp}.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
