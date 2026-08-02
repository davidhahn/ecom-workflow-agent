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
    # Set only for rule_based categories (sql) — a reason per failed
    # sub-check. None means "show expected/actual JSON instead" (exact_match).
    failure_reasons: list[str] | None = None


def run_case(case: dict, client: TestClient) -> CaseResult:
    category = case["category"]
    try:
        if category == "permission":
            actual = run_permission_case(case, client)
        elif category in ("sql", "rag"):
            actual, failure_reasons = (run_sql_case if category == "sql" else run_rag_case)(case, client)
            return CaseResult(case["id"], category, not failure_reasons, case["expected"], actual, failure_reasons)
        else:
            actual = DISPATCH[category](case)
    except Exception as e:
        # Fail loudly: surface the exception as `actual`, don't swallow it.
        actual = {"exception": f"{type(e).__name__}: {e}"}
        return CaseResult(case["id"], category, False, case["expected"], actual)

    return CaseResult(case["id"], category, actual == case["expected"], case["expected"], actual)


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


def render_report(results: list[CaseResult], skipped_categories: list[str]) -> str:
    sections = []

    id_width = max((len(r.id) for r in results), default=0)
    sections.append("\n".join(format_case_line(r, id_width) for r in results))

    headers = ["category", "what it tests", "n", "pass", "fail", "rate", "consequence of failure"]
    rows = []
    for category in SUPPORTED_CATEGORIES:
        cat_results = [r for r in results if r.category == category]
        n = len(cat_results)
        passed = sum(1 for r in cat_results if r.passed)
        failed = n - passed
        rate = f"{round(100 * passed / n)}%" if n else "n/a"
        meta = CATEGORY_METADATA[category]
        rows.append([category, meta["what_it_tests"], str(n), str(passed), str(failed), rate, meta["consequence"]])
    sections.append(render_markdown_table(headers, rows))

    total = len(results)
    total_passed = sum(1 for r in results if r.passed)
    overall_rate = round(100 * total_passed / total) if total else 0

    skip_width = max((len(c) for c in skipped_categories), default=0)
    skip_lines = "\n".join(
        f"{c} {'.' * max(3, skip_width - len(c) + 3)} {SKIP_REASONS.get(c, 'not yet runnable')}"
        for c in skipped_categories
    )

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    footer = (
        f"TOTAL: {total} run, {overall_rate}% pass.\n\n"
        f"SKIPPED, NOT YET RUNNABLE:\n{skip_lines}\n\n"
        f"{timestamp} | commit {commit}"
    )
    sections.append(footer)

    return "\n\n".join(sections)


def main() -> int:
    cases = load_cases()
    run_cases = [c for c in cases if c["category"] in SUPPORTED_CATEGORIES]

    skipped_categories = sorted({c["category"] for c in cases} - set(SUPPORTED_CATEGORIES))

    client = TestClient(fastapi_app, headers={HEADER_NAME: INTERNAL_PROXY_SECRET})
    results = [run_case(case, client) for case in run_cases]

    report = render_report(results, skipped_categories)
    print(report)

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS_ROOT / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(report + "\n")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
