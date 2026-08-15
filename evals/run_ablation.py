#!/usr/bin/env python3
"""Ablation re-run. One frozen 27-case set. One harness, built on run.py's
own case-runners. One system variable changed per variant.

The old evals/ablation_table.md compared rows measured in different ways.
The off-topic case count grew row to row. Latency got averaged over
different case sets each time. "Unchanged" stood in for a number nobody
had actually re-checked. This script holds the case set and the scoring
code fixed, and rebuilds each earlier system state as a temporary,
reversible patch in the current process. It doesn't check out old commits
for this: today's run.py imports things, like SYSTEM_PROMPT_VERSION and
the resilience category, that don't exist in old commits. It would crash
before running a single case there.

Four variants, one change each:
    baseline                    - v1 SQL prompt, no RAG threshold, no retry
    + prompt v2                 - v2 SQL prompt, no threshold, no retry
    + retrieval threshold       - v2 prompt, 0.46 threshold, no retry
    + bounded failure handling  - v2 prompt, 0.46 threshold, retry on (today)

Two earlier changes aren't here: "remove sql-05 issue" and "+ semantic
assertions." Both changed what the harness could measure. Neither touched
the app itself, so a frozen harness has nothing to compare them against.
See evals/ablation_table.md for where they're recorded instead.

Usage:
    cd apps/api
    poetry run python ../../evals/run_ablation.py

Writes evals/ablation_raw.json and evals/ablation_table.md.
"""

import json
import os
import statistics
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
EVALS_ROOT = REPO_ROOT / "evals"

sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(EVALS_ROOT))

os.environ["EVAL_RATE_LIMIT_BYPASS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

import app.orchestrator.analyze_service as analyze_service_module  # noqa: E402
import app.query.claude_client as claude_client_module  # noqa: E402
import app.rag.service as rag_service_module  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402

from run import (  # noqa: E402
    _check_expected_result,
    _latest_request_log_detail,
    load_cases,
    run_mixed_case,
    run_rag_case,
    run_resilience_case,
    run_sql_case,
)

RUNS_PER_VARIANT = 3

SQL_CASE_IDS = [
    "sql-01-refund-rate-by-category",
    "sql-03-avg-days-to-refund-by-reason",
    "sql-04-blocked-column-email-attempt",
    "sql-semantic-01-home-refund-rate-denominator",
    "sql-semantic-02-electronics-order-revenue-join-fanout",
    "sql-semantic-03-approved-refund-total-status-filter",
    "sql-semantic-04-charlotte-dubois-approved-refund-count",
]
RAG_ONTOPIC_CASE_IDS = [
    "rag-01-standard-return-window",
    "rag-03-repeat-returner-flag",
    "rag-04-partial-line-refund-amount",
    "rag-05-shipping-fee-refundable",
    "rag-06-manager-approval-threshold",
    "rag-07-clearance-item-changed-mind",
    "rag-08-defective-vs-changed-mind-window",
]
RAG_OFFTOPIC_CASE_IDS = [
    "rag-09-off-topic-loyalty-program",
    "rag-10-off-topic-gift-card",
    "rag-11-off-topic-price-match",
    "rag-12-off-topic-international-shipping",
    "rag-13-off-topic-order-cancellation",
]
MIXED_CASE_IDS = [
    "mixed-01-headphones-refund-rate-and-threshold",
    "mixed-02-defective-window-compliance-audit",
    "mixed-03-region-refund-rate-and-policy-exceptions",
    "mixed-04-repeat-refund-flag-detection",
    "mixed-06-damaged-shipping-requirements",
    "mixed-07-wrong-item-window-compliance",
]
# Rule each mixed case's answer should cite - hand-derived the same way
# evals/rag_retrieval_calibration.md did. mixed-03 has none: no rule in the
# policy governs regional exceptions, so it's excluded from on-topic
# recall entirely rather than counted as a miss.
MIXED_EXPECTED_RULE = {
    "mixed-01-headphones-refund-rate-and-threshold": 6,
    "mixed-02-defective-window-compliance-audit": 2,
    "mixed-04-repeat-refund-flag-detection": 7,
    "mixed-06-damaged-shipping-requirements": 4,
    "mixed-07-wrong-item-window-compliance": 5,
}
RESILIENCE_CASE_IDS = [
    "resilience-01-sql-tool-failure",
    "resilience-02-model-timeout",
]
FROZEN_CASE_IDS = set(
    SQL_CASE_IDS + RAG_ONTOPIC_CASE_IDS + RAG_OFFTOPIC_CASE_IDS + MIXED_CASE_IDS + RESILIENCE_CASE_IDS
)

# The real v1 prompt, from git history (`git show 0ed5da2~1:.../claude_client.py`),
# before the row-vs-unit fix. Kept verbatim, not paraphrased.
V1_SQL_PROMPT = """You are a SQL analyst for an eCommerce operations database.

Given a business question, call run_sql_query with a single read-only SELECT
statement that answers it, using only the tables and columns below. Always
list columns explicitly — never use SELECT *. The customers table's email
column is not available to you and must never appear in your query.

Schema:
{schema}
"""

V2_SQL_PROMPT = claude_client_module.SYSTEM_PROMPT  # today's prompt, captured before any patching

NO_THRESHOLD = 2.0  # cosine distance never exceeds 2.0, so this never filters anything out


def _no_retry_call(client, **kwargs):
    """What every call site did before app/llm_retry.py existed: call the
    SDK directly, once, no catch. A failure just raises."""
    return client.messages.create(**kwargs), 0


@contextmanager
def variant_state(*, sql_prompt: str, threshold: float, retry_enabled: bool):
    patches = [
        patch.object(claude_client_module, "SYSTEM_PROMPT", sql_prompt),
        patch.object(rag_service_module, "RELEVANCE_THRESHOLD", threshold),
    ]
    if not retry_enabled:
        # Both modules did `from app.llm_retry import call_with_retry`, so
        # each holds its own bound name - patching app.llm_retry itself
        # wouldn't reach either of them.
        patches.append(patch.object(claude_client_module, "call_with_retry", _no_retry_call))
        patches.append(patch.object(analyze_service_module, "call_with_retry", _no_retry_call))
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


VARIANTS = [
    ("baseline", dict(sql_prompt=V1_SQL_PROMPT, threshold=NO_THRESHOLD, retry_enabled=False)),
    ("+ prompt v2", dict(sql_prompt=V2_SQL_PROMPT, threshold=NO_THRESHOLD, retry_enabled=False)),
    ("+ retrieval threshold", dict(sql_prompt=V2_SQL_PROMPT, threshold=0.46, retry_enabled=False)),
    ("+ bounded failure handling", dict(sql_prompt=V2_SQL_PROMPT, threshold=0.46, retry_enabled=True)),
]


def _mixed_retrieved_rules(client: TestClient) -> list[int | None]:
    detail = _latest_request_log_detail(client, "analyze") or {}
    chunks = detail.get("rag_chunks_retrieved") or []
    return [c["rule_number"] for c in chunks]


def run_one_case(case: dict, client: TestClient) -> dict:
    """Runs a single case once, against whatever variant_state is active.
    Returns a flat record and never raises. A crash gets recorded as a
    result here, since that's exactly what a pre-retry variant should
    produce on the resilience cases."""
    case_id = case["id"]
    category = case["category"]
    record: dict = {"case_id": case_id, "category": category, "crashed": False}
    try:
        if category in ("sql", "sql_semantic"):
            actual, _ = run_sql_case(case, client, bypass_cache=True)
            detail = _latest_request_log_detail(client, "sql") or {}
            expected_result = case["expected"].get("expected_result")
            semantic_pass = None
            if expected_result is not None and actual["status"] == "success":
                semantic_pass = not _check_expected_result(expected_result, actual["rows"])
            record.update(
                status=actual["status"],
                semantic_pass=semantic_pass,
                latency_ms=detail.get("latency_ms"),
                estimated_cost_usd=detail.get("estimated_cost_usd"),
            )
        elif category == "rag":
            # query_rag() itself never caches, but the /query/rag router
            # wrapping it does. Without this, the first variant to ask a
            # given question (baseline, run first) poisons every later
            # variant's answer to that same question.
            actual, _ = run_rag_case(case, client, bypass_cache=True)
            expected_rules = case["expected"]["must_include_rule_numbers"]
            retrieved = actual["retrieved_rules"]
            record.update(
                retrieved_count=len(retrieved),
                refused=len(retrieved) == 0,
                expected_rules=expected_rules,
                on_topic_hit=all(r in retrieved for r in expected_rules) if expected_rules else None,
            )
        elif category == "mixed":
            actual, _ = run_mixed_case(case, client, bypass_cache=True)
            retrieved = _mixed_retrieved_rules(client)
            expected_rule = MIXED_EXPECTED_RULE.get(case_id)
            record.update(
                incomplete=actual["incomplete"],
                on_topic_hit=(expected_rule in retrieved) if expected_rule is not None else None,
            )
        else:  # resilience
            actual = run_resilience_case(case)
            record.update(actual=actual, resilience_pass=(actual == case["expected"]))
    except Exception as e:
        record.update(crashed=True, exception=f"{type(e).__name__}: {e}")
    return record


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Re-run only the rag-category cases and merge into the existing "
        "evals/ablation_raw.json, instead of re-running everything. sql and "
        "mixed cases already bypass cache correctly, so a fix that only "
        "affects the rag router doesn't need to touch their data.",
    )
    args = parser.parse_args()

    cases_by_id = {c["id"]: c for c in load_cases() if c["id"] in FROZEN_CASE_IDS}
    missing = FROZEN_CASE_IDS - set(cases_by_id)
    if missing:
        raise RuntimeError(f"frozen case ids not found in evals/cases.json: {sorted(missing)}")

    ids_to_run = (
        {cid for cid in FROZEN_CASE_IDS if cases_by_id[cid]["category"] == "rag"}
        if args.rag_only
        else set(FROZEN_CASE_IDS)
    )

    kept: list[dict] = []
    if args.rag_only:
        existing = json.loads((EVALS_ROOT / "ablation_raw.json").read_text())
        kept = [r for r in existing if r["case_id"] not in ids_to_run]
        print(f"Keeping {len(kept)} existing rows, re-running {len(ids_to_run)} rag case ids.")

    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})

    raw: list[dict] = list(kept)
    for variant_name, variant_kwargs in VARIANTS:
        print(f"\n=== {variant_name} ===")
        with variant_state(**variant_kwargs):
            for run_index in range(1, RUNS_PER_VARIANT + 1):
                for case_id in sorted(ids_to_run):
                    record = run_one_case(cases_by_id[case_id], client)
                    record["variant"] = variant_name
                    record["run_index"] = run_index
                    raw.append(record)
                    status_bit = "CRASHED" if record["crashed"] else "ok"
                    print(f"  run {run_index}/{RUNS_PER_VARIANT}  {case_id:45s} {status_bit}")

    (EVALS_ROOT / "ablation_raw.json").write_text(json.dumps(raw, indent=2, default=str) + "\n")
    print("\nWrote evals/ablation_raw.json")

    report = build_report(raw)
    (EVALS_ROOT / "ablation_table.md").write_text(report + "\n")
    print("Wrote evals/ablation_table.md")


def _mean_and_spread(values: list[float]) -> str:
    if not values:
        return "n/a"
    mean = statistics.mean(values)
    return f"{mean:.3f} (range {min(values):.3f}-{max(values):.3f})"


def build_report(raw: list[dict]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    by_variant: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        by_variant[r["variant"]].append(r)

    lines = [
        "# System Evolution: Ablation Table",
        "",
        "Frozen 27-case set, same harness, one system variable changed per row. "
        f"Every variant ran {RUNS_PER_VARIANT} times against the identical case list. "
        "Each cell shows the mean and the range across those runs. "
        "Regenerated by `evals/run_ablation.py` - raw per-run data lives in `evals/ablation_raw.json`.",
        "",
        "`remove sql-05 issue` and `+ semantic assertions` aren't in this table. "
        "Both changed what the harness could measure. "
        "The app underneath stayed the same, so a frozen harness has nothing to hold it against. "
        "See the note below the table.",
        "",
        "## Table",
        "",
        "| variant | semantic SQL (n=21) | off-topic refusal (n=15) | on-topic RAG (n=36) | "
        "SQL latency (s) | SQL cost ($) | resilience (n=6) | decision |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for variant_name, _ in VARIANTS:
        rows = by_variant[variant_name]
        sql_rows = [r for r in rows if r["category"] in ("sql", "sql_semantic")]
        rag_rows = [r for r in rows if r["category"] == "rag"]
        offtopic_rows = [r for r in rag_rows if r["case_id"] in RAG_OFFTOPIC_CASE_IDS]
        ontopic_rag_rows = [r for r in rag_rows if r["case_id"] in RAG_ONTOPIC_CASE_IDS]
        mixed_rows = [r for r in rows if r["category"] == "mixed"]
        resilience_rows = [r for r in rows if r["category"] == "resilience"]

        semantic_checked = [r for r in sql_rows if r.get("semantic_pass") is not None]
        semantic_n = len(semantic_checked)
        semantic_passed = sum(1 for r in semantic_checked if r["semantic_pass"])
        semantic_cell = f"{semantic_passed}/{semantic_n}" if semantic_n else "n/a"

        refusal_n = len(offtopic_rows)
        refused = sum(1 for r in offtopic_rows if r.get("refused"))
        refusal_cell = f"{refused}/{refusal_n}" if refusal_n else "n/a"

        ontopic_hits_rag = [r for r in ontopic_rag_rows if r.get("on_topic_hit") is not None]
        ontopic_hits_mixed = [r for r in mixed_rows if r.get("on_topic_hit") is not None]
        ontopic_all = ontopic_hits_rag + ontopic_hits_mixed
        ontopic_n = len(ontopic_all)
        ontopic_passed = sum(1 for r in ontopic_all if r["on_topic_hit"])
        ontopic_cell = f"{ontopic_passed}/{ontopic_n}" if ontopic_n else "n/a"

        latencies = [r["latency_ms"] / 1000 for r in sql_rows if r.get("latency_ms") is not None]
        costs = [r["estimated_cost_usd"] for r in sql_rows if r.get("estimated_cost_usd") is not None]
        latency_cell = _mean_and_spread(latencies)
        cost_cell = _mean_and_spread(costs)

        resilience_n = len(resilience_rows)
        resilience_passed = sum(1 for r in resilience_rows if r.get("resilience_pass"))
        resilience_crashed = sum(1 for r in resilience_rows if r["crashed"])
        if resilience_crashed:
            resilience_cell = f"{resilience_passed}/{resilience_n} ({resilience_crashed} crashed)"
        else:
            resilience_cell = f"{resilience_passed}/{resilience_n}"

        decision = {
            "baseline": "reference",
            "+ prompt v2": "keep",
            "+ retrieval threshold": "keep",
            "+ bounded failure handling": "reliability invariant",
        }[variant_name]

        lines.append(
            f"| {variant_name} | {semantic_cell} | {refusal_cell} | {ontopic_cell} | "
            f"{latency_cell} | {cost_cell} | {resilience_cell} | {decision} |"
        )

    lines += [
        "",
        "## What each column means",
        "",
        "- **semantic SQL**: the 7 `sql`/`sql_semantic` cases with a hand-derived expected value, "
        f"checked against the real returned rows, {RUNS_PER_VARIANT} runs each (n=21).",
        "- **off-topic refusal**: the 5 off-topic `rag` cases, counted as refused only when "
        f"`/query/rag` returns zero chunks, {RUNS_PER_VARIANT} runs each (n=15).",
        "- **on-topic RAG**: the 7 on-topic `rag` cases plus 5 of the 6 relevant `mixed` cases "
        "(`mixed-03` excluded - no rule in the policy governs its question, so there's nothing to "
        f"retrieve), {RUNS_PER_VARIANT} runs each (n=36). Counts as a hit when the expected rule "
        "number appears anywhere in the retrieved chunks.",
        "- **SQL latency / cost**: mean and range across the same 21 SQL calls used for the semantic "
        "column. Every row uses this same definition, never a whole-suite average.",
        "- **resilience**: the 2 mocked-failure cases, 3 runs each (n=6). Before the retry wrapper "
        "existed, a mocked failure just raised. The table shows that as a crash, because that's "
        "what happened to the request.",
        "",
        "## Rows not in this table",
        "",
        "- **remove sql-05 issue** (2026-08-04): replaced a flawed test case with a direct test of "
        "the safety layer. SQL generation itself never changed. Nothing for a frozen harness to "
        "compare against, since there's no app behavior on either side of this change.",
        "- **+ semantic assertions** (2026-08-08 to 09): gave the `sql`/`sql_semantic` cases a real "
        "expected value to check, instead of just query shape. This is the harness reaching the "
        "capability every row above now uses (`semantic SQL`). The app held still that day. Only "
        "what could be seen changed. `evals/sql_semantic_calibration_v1.md` has the number this "
        "capability first found: 66.7%, before prompt v2 fixed it.",
        "",
        f"Generated {timestamp}.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
