"""Catches refund_policy.md and refund_evaluator.py's constants drifting
apart. Each regex matches the doc's exact current wording, not general
prose - if the doc's wording changes, update the regex to match, don't
make it more flexible."""

import re
from pathlib import Path

from app.orchestrator.refund_evaluator import (
    APPROVAL_THRESHOLD_CENTS,
    REASON_WINDOW_DAYS,
    REPEAT_REFUND_THRESHOLD,
    REPEAT_REFUND_WINDOW_DAYS,
)

POLICY_PATH = Path(__file__).resolve().parents[3] / "docs" / "policies" / "refund_policy.md"


def _section(heading: str) -> str:
    """Prose under a single '## <heading>' section, up to the next '## ' or
    end of file."""
    text = POLICY_PATH.read_text()
    match = re.search(rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    assert match, f"expected a '## {heading}' section in {POLICY_PATH}"
    return match.group(1)


def _days(section: str, phrase: str) -> int:
    """Integer immediately preceding a fixed phrase, e.g. '90 days from the
    purchase date'."""
    match = re.search(rf"(\d+) {re.escape(phrase)}", section)
    assert match, f"expected '<N> {phrase}' in section: {section!r}"
    return int(match.group(1))


def test_defective_window_matches_policy():
    section = _section("Defective Items")
    assert _days(section, "days from the purchase date") == REASON_WINDOW_DAYS["defective"]


def test_changed_mind_window_matches_policy():
    section = _section("Changed Mind")
    assert _days(section, "days of the purchase date") == REASON_WINDOW_DAYS["changed_mind"]


def test_damaged_shipping_has_no_time_limit_in_policy_and_code():
    section = _section("Damaged in Shipping")
    assert "no time limit" in section
    assert REASON_WINDOW_DAYS["damaged_shipping"] is None


def test_wrong_item_has_no_time_limit_in_policy_and_code():
    section = _section("Wrong Item Shipped")
    assert "no time limit" in section
    assert REASON_WINDOW_DAYS["wrong_item"] is None


def test_approval_threshold_matches_policy():
    section = _section("Approval Threshold")
    match = re.search(r"\$(\d+)", section)
    assert match, f"expected a dollar amount in section: {section!r}"
    assert int(match.group(1)) * 100 == APPROVAL_THRESHOLD_CENTS


def test_repeat_refund_threshold_and_window_match_policy():
    section = _section("Repeat-Refund Flag")
    threshold_match = re.search(r"(\d+) or more approved refunds", section)
    window_match = re.search(r"rolling (\d+)-day window", section)
    assert threshold_match and window_match, f"unexpected wording: {section!r}"
    assert int(threshold_match.group(1)) == REPEAT_REFUND_THRESHOLD
    assert int(window_match.group(1)) == REPEAT_REFUND_WINDOW_DAYS
