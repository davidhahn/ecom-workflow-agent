#!/usr/bin/env python3
"""Eval runner for evals/cases.json.

Runs the categories with a working automated harness (refund_evaluator,
groundedness, topic_coverage, permission, sql, rag) against the real
functions/endpoints they test. Prints a report and writes it to
evals/results/<timestamp>/report.md.

Usage (from apps/api, so poetry deps and .env resolve like the pytest suite):

    cd apps/api
    poetry run python ../../evals/run.py

Needs the seeded Postgres instance running — refund_evaluator, permission,
sql, and rag cases hit the real database, not a mock. sql also calls the
real /query/sql endpoint (and Claude), so it's not free or fully
deterministic like the rest. rag hits the real /query/rag endpoint too, but
that's embedding + cosine search, no LLM call, so it stays deterministic.
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
CASES_PATH = REPO_ROOT / "evals" / "cases.json"
RESULTS_ROOT = REPO_ROOT / "evals" / "results"

sys.path.insert(0, str(API_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.orchestrator.groundedness import check_groundedness  # noqa: E402
from app.orchestrator.refund_evaluator import evaluate_refund, resolve_order_item  # noqa: E402
from app.orchestrator.topic_coverage import check_topic_coverage  # noqa: E402
from app.proxy_secret import HEADER_NAME, INTERNAL_PROXY_SECRET  # noqa: E402
from app.rag.schemas import chunk_from_dict  # noqa: E402

# ---------------------------------------------------------------------------
# category metadata (order here is the order they render in)
# ---------------------------------------------------------------------------

CATEGORY_METADATA = {
    "refund_evaluator": {
        "what_it_tests": "money-decision waterfall",
        "consequence": "wrong refund decisions",
    },
    "groundedness": {
        "what_it_tests": "citation detector works",
        "consequence": "broken trust signal",
    },
    "topic_coverage": {
        "what_it_tests": "fabrication flag works",
        "consequence": "fake claims ship unflagged",
    },
    "permission": {
        "what_it_tests": "role gates hold",
        "consequence": "unauthorized writes",
    },
    "sql": {
        "what_it_tests": "generated SQL structure",
        "consequence": "wrong results or leaked columns",
    },
    "rag": {
        "what_it_tests": "policy retrieval recall",
        "consequence": "wrong or missing policy rule cited",
    },
}
SUPPORTED_CATEGORIES = list(CATEGORY_METADATA.keys())

# Categories with no runner yet (see EVALS.md's "Out of scope"), and why.
SKIP_REASONS = {
    "mixed": "needs judge",
    "prompt_injection": "needs judge; one case is image-only",
    "ticket_evaluator": "needs harness (draft/confirm flow)",
    "invoice_evaluator": "needs harness (draft/confirm flow)",
}

# ---------------------------------------------------------------------------
# evaluate_refund() takes structured fields, not raw text — running case
# text through it would mean calling the LLM extractor, which this category
# is designed to avoid. REFUND_FIXTURES hand-resolves each case's text into
# those fields, checked against what seed.py actually seeds.
# ---------------------------------------------------------------------------

REFUND_FIXTURES: dict[str, dict] = {
    "refund-01-baseline-approval-damaged-shipping": {
        "customer": "James O'Brien",
        "product": "Ceramic Coffee Mug",
        "reason": "damaged_shipping",
        "evidence_submitted": True,
    },
    "refund-02-category-exclusion-final-sale": {
        "customer": "Mia Fischer",
        "product": "Last-Season Winter Jacket",
        "reason": "changed_mind",
        "evidence_submitted": False,
    },
    "refund-03-final-sale-exempt-reason-override": {
        "customer": "Mia Fischer",
        "product": "Last-Season Winter Jacket",
        "reason": "wrong_item",
        "evidence_submitted": False,
    },
    "refund-04-time-window-violation-changed-mind": {
        "customer": "Noah Martinez",
        "product": "Ergonomic Desk Chair",
        "reason": "changed_mind",
        "evidence_submitted": False,
    },
    "refund-05-time-window-violation-defective": {
        "customer": "Liam Patel",
        "product": "Bluetooth Headphones Pro",
        "reason": "defective",
        "evidence_submitted": False,
    },
    "refund-06-evidence-missing-damaged-shipping": {
        "customer": "Benjamin Wright",
        "product": "Cotton Bath Towel Set",
        "reason": "damaged_shipping",
        "evidence_submitted": False,
    },
    "refund-07-repeat-refund-flag-charlotte-dubois": {
        "customer": "Charlotte Dubois",
        "product": "Wireless Keyboard",
        "reason": "wrong_item",
        "evidence_submitted": False,
    },
    # reason=None means the text doesn't map to a reason code — same
    # short-circuit refund_service.py takes, no DB lookup needed.
    "refund-08-could-not-process-ambiguous-reason": {
        "customer": "Ava Thompson",
        "product": "Wireless Mouse",
        "reason": None,
        "evidence_submitted": False,
    },
    "refund-09-could-not-process-unresolvable-product": {
        "customer": "Ava Thompson",
        "product": "Instant Pot Pressure Cooker",
        "reason": "defective",
        "evidence_submitted": False,
    },
    "refund-10-repeat-refund-flag-not-triggered-below-threshold": {
        "customer": "Noah Martinez",
        "product": "Wireless Mouse",
        "reason": "defective",
        "evidence_submitted": False,
    },
    "refund-11-over-threshold-needs-manager": {
        "customer": "Henry Osei",
        "product": "Ergonomic Desk Chair",
        "reason": "wrong_item",
        "evidence_submitted": False,
    },
    "refund-12-repeat-refund-flag-damaged-shipping-with-evidence": {
        "customer": "Charlotte Dubois",
        "product": "Wireless Keyboard",
        "reason": "damaged_shipping",
        "evidence_submitted": True,
    },
}


def run_refund_evaluator_case(case: dict) -> dict:
    fixture = REFUND_FIXTURES[case["id"]]
    if fixture["reason"] is None:
        return {"status": "could_not_process", "rule_applied": None}

    resolved = resolve_order_item(fixture["product"], fixture["customer"])
    if resolved is None:
        return {"status": "could_not_process", "rule_applied": None}

    evaluation = evaluate_refund(
        order_item_id=resolved.order_item_id,
        reason=fixture["reason"],
        evidence_submitted=fixture["evidence_submitted"],
        requested_at=datetime.now(timezone.utc),
    )
    return {"status": evaluation.status, "rule_applied": evaluation.rule_applied}


def run_groundedness_case(case: dict) -> dict:
    fixture = json.loads(case["input"])
    chunks = [chunk_from_dict(chunk) for chunk in fixture["retrieved_chunks"]]
    grounded, ungrounded_claims = check_groundedness(fixture["answer"], chunks)
    return {"grounded": grounded, "ungrounded_claims": ungrounded_claims}


def run_topic_coverage_case(case: dict) -> dict:
    fixture = json.loads(case["input"])
    warning = check_topic_coverage(fixture["answer"], fixture["sql_used"], fixture["generated_sql"])
    return {"topic_coverage_warning": warning}


def run_permission_case(case: dict, client: TestClient) -> dict:
    fixture = json.loads(case["input"])
    response = client.post(
        fixture["endpoint"],
        json=fixture["body"],
        headers={"X-Demo-Role": fixture["role"]},
    )
    return {"status_code": response.status_code}


# request_type strings match what /observability/requests filters on, per
# apps/api/app/observability/router.py's RequestType literal.
ENDPOINT_REQUEST_TYPE = {
    "/query/sql": "sql",
    "/query/rag": "rag",
    "/tickets/draft": "ticket_draft",
    "/tickets/confirm": "ticket_confirm",
}


def _latest_cost_usd(client: TestClient, request_type: str) -> float | None:
    """Cost isn't in any endpoint's response body — only request_log has it.
    Safe to just take the most recent row: run.py calls everything
    sequentially, so it's always the row this case just created."""
    rows = client.get("/observability/requests", params={"request_type": request_type, "limit": 1}).json()
    rows = rows["requests"]
    return rows[0]["estimated_cost_usd"] if rows else None


# ---------------------------------------------------------------------------
# sql: rule_based, not exact_match — checks structural properties of the
# real generated SQL via substring matching, not a parser. See evals/
# README.md for the known-limitation writeup.
# ---------------------------------------------------------------------------

WRITE_VERB_SUBSTRINGS = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "grant ", "revoke "]


def _check_tables_joined(sql_lower: str, tables: list[str]) -> list[str]:
    return [f"table `{t}` missing from generated SQL" for t in tables if t.lower() not in sql_lower]


def _check_forbidden_columns(sql_lower: str, columns: list[str], property_name: str) -> list[str]:
    return [
        f"column `{c}` must not appear in generated SQL ({property_name})"
        for c in columns
        if c.lower() in sql_lower
    ]


def _check_read_only_violation_attempt(sql_lower: str, expected_attempt: bool) -> list[str]:
    has_write_verb = any(verb in sql_lower for verb in WRITE_VERB_SUBSTRINGS)
    if expected_attempt and not has_write_verb:
        return ["expected read_only_violation_attempt=true, generated SQL has no write-verb substring"]
    if not expected_attempt and has_write_verb:
        return ["expected read_only_violation_attempt=false, generated SQL contains a write-verb substring"]
    return []


def run_sql_case(case: dict, client: TestClient) -> tuple[dict, list[str]]:
    expected = case["expected"]
    response = client.post("/query/sql", json={"question": case["input"]})
    body = response.json()
    actual_status = body.get("status")
    sql_executed = body.get("sql_executed") or ""
    sql_lower = sql_executed.lower()

    failure_reasons: list[str] = []
    if "tables_joined" in expected:
        failure_reasons += _check_tables_joined(sql_lower, expected["tables_joined"])
    if "columns_excluded" in expected:
        failure_reasons += _check_forbidden_columns(sql_lower, expected["columns_excluded"], "columns_excluded")
    if "must_not_select" in expected:
        failure_reasons += _check_forbidden_columns(sql_lower, expected["must_not_select"], "must_not_select")
    if "read_only_violation_attempt" in expected:
        failure_reasons += _check_read_only_violation_attempt(sql_lower, expected["read_only_violation_attempt"])
    if "expected_status" in expected and actual_status != expected["expected_status"]:
        failure_reasons.append(f"expected status: {expected['expected_status']}")
        failure_reasons.append(f"actual status:   {actual_status}")
    # expected_rejection_layer isn't checked — /query/sql never returns
    # which layer rejected a query, only rejection_reason and status.

    actual = {"status": actual_status, "sql_executed": sql_executed}
    return actual, failure_reasons


# ---------------------------------------------------------------------------
# rag: recall only — did the labeled rule come back in top-k. Doesn't check
# for irrelevant chunks or whether an answer would use the rule correctly.
# ---------------------------------------------------------------------------


def run_rag_case(case: dict, client: TestClient) -> tuple[dict, list[str]]:
    expected_rules = case["expected"]["must_include_rule_numbers"]
    response = client.post("/query/rag", json={"question": case["input"]})
    body = response.json()
    retrieved_rules = [chunk["rule_number"] for chunk in body.get("chunks", [])]

    missing = [rule for rule in expected_rules if rule not in retrieved_rules]
    failure_reasons: list[str] = []
    if missing:
        failure_reasons.append(f"expected rule: {missing[0] if len(missing) == 1 else missing}")
        failure_reasons.append(f"retrieved rules: {retrieved_rules}")

    return {"retrieved_rules": retrieved_rules}, failure_reasons


# ---------------------------------------------------------------------------
# cache: not a cases.json category — a deterministic regression check that
# the same /query/sql question is served from cache the second time, with
# zero tokens and zero cost on the hit. Mirrors
# apps/api/tests/test_sql_caching.py, plus records latency/tokens/cost.
# ---------------------------------------------------------------------------

CACHE_CHECK_QUESTION = "How many products are in the Office category? (eval cache check, unique phrasing)"


@dataclass
class CacheCheckResult:
    passed: bool
    failure_reasons: list[str]
    first_cached: bool
    second_cached: bool
    first_latency_ms: int
    second_latency_ms: int
    first_tokens: tuple[int | None, int | None]
    second_tokens: tuple[int | None, int | None]
    first_cost_usd: float | None
    second_cost_usd: float | None


def run_cache_check(client: TestClient) -> CacheCheckResult:
    first = client.post("/query/sql", json={"question": CACHE_CHECK_QUESTION}).json()
    second = client.post("/query/sql", json={"question": CACHE_CHECK_QUESTION}).json()

    logs = client.get("/observability/requests", params={"request_type": "sql", "limit": 2}).json()["requests"]
    second_log, first_log = logs[0], logs[1]

    reasons: list[str] = []
    if first["cached"] is not False:
        reasons.append(f"expected first call cached=false, got cached={first['cached']}")
    if second["cached"] is not True:
        reasons.append(f"expected second call cached=true, got cached={second['cached']}")
    if second["status"] != first["status"]:
        reasons.append(f"cache hit returned a different status: first={first['status']} second={second['status']}")
    if second["rows"] != first["rows"]:
        reasons.append("cache hit returned different rows than the original call")
    if (second_log["input_tokens"], second_log["output_tokens"]) not in ((0, 0), (None, None)):
        reasons.append(
            f"expected zero token usage on cache hit, got "
            f"input={second_log['input_tokens']} output={second_log['output_tokens']}"
        )
    if second_log["estimated_cost_usd"] not in (0, 0.0, None):
        reasons.append(f"expected $0 cost on cache hit, got ${second_log['estimated_cost_usd']}")

    return CacheCheckResult(
        passed=not reasons,
        failure_reasons=reasons,
        first_cached=first["cached"],
        second_cached=second["cached"],
        first_latency_ms=first_log["latency_ms"],
        second_latency_ms=second_log["latency_ms"],
        first_tokens=(first_log["input_tokens"], first_log["output_tokens"]),
        second_tokens=(second_log["input_tokens"], second_log["output_tokens"]),
        first_cost_usd=first_log["estimated_cost_usd"],
        second_cost_usd=second_log["estimated_cost_usd"],
    )


DISPATCH = {
    "refund_evaluator": run_refund_evaluator_case,
    "groundedness": run_groundedness_case,
    "topic_coverage": run_topic_coverage_case,
}


# ---------------------------------------------------------------------------
# running + recording
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    id: str
    category: str
    passed: bool
    expected: dict
    actual: dict
    # Set only for rule_based categories (sql, rag) — a reason per failed
    # sub-check. None means "show expected/actual JSON instead" (exact_match).
    failure_reasons: list[str] | None = None
    latency_ms: float = 0.0
    # $0 for categories that never touch a paid API (refund_evaluator,
    # groundedness, topic_coverage — pure functions, no LLM call, ever).
    # None for a call that failed before any cost could be looked up.
    cost_usd: float | None = 0.0


def run_case(case: dict, client: TestClient) -> CaseResult:
    category = case["category"]
    start = time.perf_counter()
    try:
        if category == "permission":
            actual = run_permission_case(case, client)
            fixture = json.loads(case["input"])
            request_type = ENDPOINT_REQUEST_TYPE.get(fixture["endpoint"])
            cost_usd = _latest_cost_usd(client, request_type) if request_type else 0.0
            failure_reasons = None
        elif category in ("sql", "rag"):
            actual, failure_reasons = (run_sql_case if category == "sql" else run_rag_case)(case, client)
            cost_usd = _latest_cost_usd(client, category)
        else:
            actual = DISPATCH[category](case)
            failure_reasons = None
            cost_usd = 0.0  # no endpoint call, no LLM call
    except Exception as e:
        # Fail loudly: surface the exception as `actual`, don't swallow it.
        latency_ms = (time.perf_counter() - start) * 1000
        actual = {"exception": f"{type(e).__name__}: {e}"}
        return CaseResult(case["id"], category, False, case["expected"], actual, None, latency_ms, None)

    latency_ms = (time.perf_counter() - start) * 1000
    passed = not failure_reasons if failure_reasons is not None else actual == case["expected"]
    return CaseResult(case["id"], category, passed, case["expected"], actual, failure_reasons, latency_ms, cost_usd)


def load_cases() -> list[dict]:
    with open(CASES_PATH) as f:
        cases = json.load(f)

    refund_case_ids = {c["id"] for c in cases if c["category"] == "refund_evaluator"}
    if refund_case_ids != set(REFUND_FIXTURES.keys()):
        missing = refund_case_ids - set(REFUND_FIXTURES.keys())
        extra = set(REFUND_FIXTURES.keys()) - refund_case_ids
        raise RuntimeError(
            "REFUND_FIXTURES is out of sync with evals/cases.json "
            f"(missing fixtures: {sorted(missing)}, stale fixtures: {sorted(extra)})"
        )
    return cases


# ---------------------------------------------------------------------------
# console + file report
# ---------------------------------------------------------------------------


def format_case_line(result: CaseResult, id_width: int) -> str:
    status = "PASS" if result.passed else "FAIL"
    dots = "." * max(3, id_width - len(result.id) + 3)
    line = f"{result.id} {dots} {status}"
    if result.passed:
        return line
    if result.failure_reasons is not None:
        reasons = "\n".join(f"    {reason}" for reason in result.failure_reasons)
        return f"{line}\n{reasons}"
    return (
        f"{line}\n"
        f"    expected: {json.dumps(result.expected)}\n"
        f"    actual:   {json.dumps(result.actual)}"
    )


def render_cache_check(result: CacheCheckResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    lines = [
        f"cache-01-repeated-sql-question ... {status}",
        f"    first call:  cached={result.first_cached} latency={result.first_latency_ms}ms "
        f"tokens=(in:{result.first_tokens[0]}, out:{result.first_tokens[1]}) cost=${result.first_cost_usd}",
        f"    second call: cached={result.second_cached} latency={result.second_latency_ms}ms "
        f"tokens=(in:{result.second_tokens[0]}, out:{result.second_tokens[1]}) cost=${result.second_cost_usd}",
    ]
    lines.extend(f"    {reason}" for reason in result.failure_reasons)
    return "\n".join(lines)


COMPARISON_READY_THRESHOLD = 8


@dataclass
class CategoryStats:
    category: str
    n: int
    passed: int
    failed: int
    pass_rate: float
    mean_latency_ms: float
    mean_cost_usd: float
    comparison_ready: bool


def compute_category_stats(results: list[CaseResult]) -> list[CategoryStats]:
    stats = []
    for category in SUPPORTED_CATEGORIES:
        cat_results = [r for r in results if r.category == category]
        n = len(cat_results)
        if n == 0:
            continue
        passed = sum(1 for r in cat_results if r.passed)
        stats.append(
            CategoryStats(
                category=category,
                n=n,
                passed=passed,
                failed=n - passed,
                pass_rate=100 * passed / n,
                mean_latency_ms=sum(r.latency_ms for r in cat_results) / n,
                mean_cost_usd=sum(r.cost_usd or 0.0 for r in cat_results) / n,
                comparison_ready=n >= COMPARISON_READY_THRESHOLD,
            )
        )
    return stats


def _fmt_latency(ms: float) -> str:
    return f"{ms / 1000:.2f}s"


def _fmt_cost(usd: float) -> str:
    return f"${usd:.3f}"


def comparison_readiness_note(stats: list[CategoryStats]) -> str:
    small = [s for s in stats if not s.comparison_ready]
    small_list = ", ".join(f"`{s.category}` (n={s.n})" for s in small)
    lines = [
        f"Categories with n >= {COMPARISON_READY_THRESHOLD} may be used for directional before-and-after comparison.",
        "",
    ]
    if small:
        lines.append(
            f"{small_list} fall below that threshold and are treated as regression checks. Their "
            "individual pass or fail results may be reported, but their percentages should not be "
            "presented as evidence of quality improvement."
        )
        lines.append("")
    lines.append("This threshold is a practical reporting rule for the sprint, not a claim of statistical significance.")
    return "\n".join(lines)


def render_overall_summary(
    results: list[CaseResult],
    cache_result: CacheCheckResult,
    skipped_categories: list[str],
    timestamp: str,
    commit: str,
) -> str:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = round(100 * passed / total) if total else 0
    mean_latency_ms = sum(r.latency_ms for r in results) / total if total else 0.0
    mean_cost_usd = sum(r.cost_usd or 0.0 for r in results) / total if total else 0.0

    return "\n".join(
        [
            f"Total: {total} run, {passed} passed, {failed} failed ({pass_rate}% pass rate)",
            f"Mean latency: {_fmt_latency(mean_latency_ms)} | Mean cost: {_fmt_cost(mean_cost_usd)}",
            f"Cache check: {'PASS' if cache_result.passed else 'FAIL'}",
            f"Skipped categories: {', '.join(skipped_categories)}",
            f"{timestamp} | commit {commit}",
        ]
    )


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def render_row(cells: list[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)) + " |"

    lines = [render_row(headers), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    lines.extend(render_row(row) for row in rows)
    return "\n".join(lines)


def render_report(
    results: list[CaseResult],
    skipped_categories: list[str],
    cache_result: CacheCheckResult,
    stats: list[CategoryStats],
    timestamp: str,
    commit: str,
) -> str:
    sections = []

    id_width = max((len(r.id) for r in results), default=0)
    sections.append("\n".join(format_case_line(r, id_width) for r in results))

    # Not a cases.json category — a deterministic regression check, kept out
    # of the quality tables below rather than made to look like one.
    sections.append(
        "CACHE CHECK (deterministic regression, not an AI-quality category):\n" + render_cache_check(cache_result)
    )

    headers = [
        "category",
        "what it tests",
        "n",
        "pass",
        "fail",
        "rate",
        "mean latency",
        "mean cost",
        "consequence of failure",
    ]
    rows = [
        [
            s.category,
            CATEGORY_METADATA[s.category]["what_it_tests"],
            str(s.n),
            str(s.passed),
            str(s.failed),
            f"{round(s.pass_rate)}%",
            _fmt_latency(s.mean_latency_ms),
            _fmt_cost(s.mean_cost_usd),
            CATEGORY_METADATA[s.category]["consequence"],
        ]
        for s in stats
    ]
    sections.append(render_markdown_table(headers, rows))
    sections.append(comparison_readiness_note(stats))

    skip_width = max((len(c) for c in skipped_categories), default=0)
    skip_lines = "\n".join(
        f"{c} {'.' * max(3, skip_width - len(c) + 3)} {SKIP_REASONS.get(c, 'not yet runnable')}"
        for c in skipped_categories
    )
    sections.append(f"SKIPPED, NOT YET RUNNABLE:\n{skip_lines}")

    sections.append(render_overall_summary(results, cache_result, skipped_categories, timestamp, commit))

    return "\n\n".join(sections)


def build_results_json(
    results: list[CaseResult],
    skipped_categories: list[str],
    cache_result: CacheCheckResult,
    stats: list[CategoryStats],
    timestamp: str,
    commit: str,
) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    return {
        "timestamp": timestamp,
        "commit": commit,
        "cases": [
            {
                "id": r.id,
                "category": r.category,
                "passed": r.passed,
                "expected": r.expected,
                "actual": r.actual,
                "failure_reasons": r.failure_reasons,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
            }
            for r in results
        ],
        "categories": [
            {
                "category": s.category,
                "n": s.n,
                "passed": s.passed,
                "failed": s.failed,
                "pass_rate": s.pass_rate,
                "mean_latency_ms": s.mean_latency_ms,
                "mean_cost_usd": s.mean_cost_usd,
                "comparison_ready": s.comparison_ready,
                "what_it_tests": CATEGORY_METADATA[s.category]["what_it_tests"],
                "consequence_of_failure": CATEGORY_METADATA[s.category]["consequence"],
            }
            for s in stats
        ],
        "comparison_readiness": {
            "threshold_n": COMPARISON_READY_THRESHOLD,
            "note": "Categories with n below this threshold are regression checks, not comparison evidence.",
        },
        "cache_check": {
            "passed": cache_result.passed,
            "failure_reasons": cache_result.failure_reasons,
            "first_cached": cache_result.first_cached,
            "second_cached": cache_result.second_cached,
            "first_latency_ms": cache_result.first_latency_ms,
            "second_latency_ms": cache_result.second_latency_ms,
            "first_tokens": cache_result.first_tokens,
            "second_tokens": cache_result.second_tokens,
            "first_cost_usd": cache_result.first_cost_usd,
            "second_cost_usd": cache_result.second_cost_usd,
        },
        "skipped_categories": skipped_categories,
        "overall": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": 100 * passed / total if total else 0,
            "mean_latency_ms": sum(r.latency_ms for r in results) / total if total else 0.0,
            "mean_cost_usd": sum(r.cost_usd or 0.0 for r in results) / total if total else 0.0,
        },
    }


def main() -> int:
    cases = load_cases()
    run_cases = [c for c in cases if c["category"] in SUPPORTED_CATEGORIES]

    skipped_categories = sorted({c["category"] for c in cases} - set(SUPPORTED_CATEGORIES))

    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})
    results = [run_case(case, client) for case in run_cases]
    cache_result = run_cache_check(client)
    stats = compute_category_stats(results)

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = render_report(results, skipped_categories, cache_result, stats, timestamp, commit)
    print(report)

    results_json = build_results_json(results, skipped_categories, cache_result, stats, timestamp, commit)

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS_ROOT / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(report + "\n")
    (out_dir / "results.json").write_text(json.dumps(results_json, indent=2) + "\n")

    return 0 if all(r.passed for r in results) and cache_result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
