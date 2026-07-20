"""Tests for the two-call draft/confirm vendor-invoice write flow — reuses
the exact draft/confirm mechanism proven by test_tickets.py. The Claude
image-extraction call is mocked so the deterministic validation checks
(arithmetic mismatch, duplicate detection, low-confidence flagging) can be
driven by fixed extraction output rather than depending on what a real
Claude call happens to read off a real invoice image; everything downstream
of extraction (validation, draft store, Postgres writes) is real, matching
this project's established testing style.
"""

import dataclasses
import time
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from sqlalchemy import desc, func, select

from app.db.models import VendorInvoice
from app.db.observability_models import RequestLog
from app.db.session import SessionLocal
from app.invoices.draft_store import create_draft
from app.invoices.service import confirm_invoice, draft_invoice
from app.tools.registry import TOOLS

FAKE_IMAGE_B64 = "ZmFrZS1pbWFnZS1ieXRlcw=="  # arbitrary base64 — extraction is mocked

# vendor_invoices has a real unique constraint on (vendor_name, invoice_number)
# and nothing truncates it between test runs (unlike support_tickets, which has
# no such constraint) — invoice numbers must be unique per run, not just per
# test, or a rerun collides with rows a previous run already committed.
_RUN_ID = uuid.uuid4().hex[:8]


def _unique_invoice_number(label: str) -> str:
    return f"INV-{label}-{_RUN_ID}"


def _invoice_count() -> int:
    with SessionLocal() as session:
        return session.execute(select(func.count(VendorInvoice.id))).scalar_one()


def _fake_extraction_response(
    *,
    vendor_name: str,
    invoice_number: str,
    invoice_date_str: str = "2026-06-01",
    subtotal_cents: int = 10000,
    tax_cents: int = 800,
    total_cents: int = 10800,
    field_confidence: dict | None = None,
):
    confidence = field_confidence or {
        "vendor_name": 0.95,
        "invoice_number": 0.95,
        "invoice_date": 0.95,
        "subtotal_cents": 0.95,
        "tax_cents": 0.95,
        "total_cents": 0.95,
    }
    fake_tool_use = MagicMock(
        type="tool_use",
        input={
            "vendor_name": vendor_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date_str,
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "line_items": [],
            "field_confidence": confidence,
        },
    )
    fake_usage = MagicMock(input_tokens=100, output_tokens=50)
    return MagicMock(content=[fake_tool_use], stop_reason="tool_use", usage=fake_usage)


def _draft_invoice_mocked(**kwargs):
    with patch("app.invoices.extraction.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = _fake_extraction_response(**kwargs)
        return draft_invoice(FAKE_IMAGE_B64, "image/png")


def test_draft_does_not_write_to_vendor_invoices():
    before = _invoice_count()

    result = _draft_invoice_mocked(
        vendor_name="Acme Supply Co", invoice_number=_unique_invoice_number("DRAFT-NOWRITE")
    )

    assert result.status == "drafted"
    assert result.draft_id is not None
    assert _invoice_count() == before


def test_arithmetic_mismatch_flags_correctly():
    result = _draft_invoice_mocked(
        vendor_name="Acme Supply Co",
        invoice_number=_unique_invoice_number("ARITH-MISMATCH"),
        subtotal_cents=10000,
        tax_cents=800,
        total_cents=99999,  # deliberately inconsistent with subtotal + tax
    )

    assert result.status == "drafted"
    assert result.validation_status == "flagged"
    assert any("total_cents" in reason for reason in result.flagged_reasons)


def test_low_confidence_dollar_field_flags_correctly():
    result = _draft_invoice_mocked(
        vendor_name="Acme Supply Co",
        invoice_number=_unique_invoice_number("LOWCONF"),
        field_confidence={
            "vendor_name": 0.95,
            "invoice_number": 0.95,
            "invoice_date": 0.95,
            "subtotal_cents": 0.4,  # deliberately below the 0.7 threshold
            "tax_cents": 0.95,
            "total_cents": 0.95,
        },
    )

    assert result.status == "drafted"
    assert result.validation_status == "flagged"
    assert any("subtotal_cents" in reason for reason in result.flagged_reasons)


def test_confirm_writes_exactly_once_not_duplicated_on_retry():
    before = _invoice_count()

    draft = _draft_invoice_mocked(
        vendor_name="Acme Supply Co", invoice_number=_unique_invoice_number("CONFIRM-ONCE")
    )
    assert draft.status == "drafted"

    first_confirm = confirm_invoice(draft.draft_id)
    assert first_confirm.status == "created"
    assert first_confirm.invoice_id is not None
    assert _invoice_count() == before + 1

    second_confirm = confirm_invoice(draft.draft_id)
    assert second_confirm.status == "created"
    assert second_confirm.invoice_id == first_confirm.invoice_id
    assert _invoice_count() == before + 1  # still +1, not +2


def test_duplicate_vendor_invoice_number_caught_at_draft_time():
    vendor_name = "Acme Supply Co"
    invoice_number = _unique_invoice_number("DUPLICATE-DRAFT")

    first_draft = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    assert confirm_invoice(first_draft.draft_id).status == "created"

    second_draft = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    assert second_draft.status == "drafted"
    assert second_draft.validation_status == "duplicate"


def test_duplicate_submitted_between_draft_time_and_confirm_time_caught_at_confirm():
    """Simulates the race the task calls out explicitly: draft two invoices
    with the same (vendor_name, invoice_number) before either is confirmed —
    neither is a duplicate yet at draft-time, since neither exists in the
    table. Confirming the first is fine; confirming the second must still be
    caught as a duplicate at confirm-time, not waved through just because
    its draft-time validation said 'validated'. vendor_invoices has a unique
    index on (vendor_name, invoice_number), so the second confirm must
    refuse to insert rather than raise an IntegrityError."""
    vendor_name = "Acme Supply Co"
    invoice_number = _unique_invoice_number("DUPLICATE-RACE")

    draft_a = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    draft_b = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    assert draft_a.validation_status == "validated"
    assert draft_b.validation_status == "validated"

    before = _invoice_count()

    confirm_a = confirm_invoice(draft_a.draft_id)
    assert confirm_a.status == "created"
    assert confirm_a.validation_status == "validated"
    assert _invoice_count() == before + 1

    confirm_b = confirm_invoice(draft_b.draft_id)
    assert confirm_b.status == "error"
    assert confirm_b.validation_status == "duplicate"
    assert confirm_b.invoice_id is None
    assert confirm_b.error_reason is not None
    assert _invoice_count() == before + 1  # still just the one row, not two


def test_duplicate_confirm_rejection_is_logged_with_full_invoice_detail():
    """vendor_invoices never gets a row for a rejected duplicate (the unique
    index forbids it) — request_log is the only audit trail a human has for
    investigating a duplicate-confirm attempt. Asserts the actual detail
    (vendor, invoice number, date, amounts, line items), not just that a row
    with request_type='invoice_confirm' exists — a bare status flag with no
    underlying content wouldn't let a reviewer distinguish one duplicate
    attempt from another."""
    vendor_name = "Acme Supply Co"
    invoice_number = _unique_invoice_number("DUPLICATE-LOGGED")

    draft_a = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    draft_b = _draft_invoice_mocked(vendor_name=vendor_name, invoice_number=invoice_number)
    assert confirm_invoice(draft_a.draft_id).status == "created"

    confirm_b = confirm_invoice(draft_b.draft_id)
    assert confirm_b.status == "error"
    assert confirm_b.validation_status == "duplicate"

    with SessionLocal() as session:
        row = (
            session.execute(
                select(RequestLog)
                .where(RequestLog.request_type == "invoice_confirm")
                .where(RequestLog.input == draft_b.draft_id)
                .order_by(desc(RequestLog.created_at))
            )
            .scalars()
            .first()
        )

    assert row is not None
    output = row.output
    assert output["status"] == "error"
    assert output["validation_status"] == "duplicate"
    assert output["vendor_name"] == vendor_name
    assert output["invoice_number"] == invoice_number
    assert output["invoice_date"] == "2026-06-01"
    assert output["subtotal_cents"] == 10000
    assert output["tax_cents"] == 800
    assert output["total_cents"] == 10800
    assert output["line_items"] == []


def test_confirm_with_missing_draft_id_returns_clear_error():
    result = confirm_invoice("this-draft-id-was-never-created")
    assert result.status == "error"
    assert result.error_reason is not None
    assert result.invoice_id is None


def test_confirm_with_expired_draft_returns_clear_error():
    draft_id = create_draft(
        {
            "vendor_name": "Acme Supply Co",
            "invoice_number": "INV-EXPIRE-001",
            "invoice_date": date(2026, 1, 1),
            "subtotal_cents": 100,
            "tax_cents": 0,
            "total_cents": 100,
            "line_items": [],
            "field_confidence": {},
            "status": "validated",
            "flagged_reasons": [],
        },
        ttl_seconds=0.01,
    )
    time.sleep(0.05)

    result = confirm_invoice(draft_id)
    assert result.status == "error"
    assert result.error_reason is not None


def test_confirm_enforces_requires_confirmation_flag(monkeypatch):
    """Proves the gate is actually read and enforced at call time, not just
    declared on the ToolSpec — flipping the flag changes real behavior."""
    stale_spec = dataclasses.replace(TOOLS["draft_vendor_invoice"], requires_confirmation=False)
    monkeypatch.setitem(TOOLS, "draft_vendor_invoice", stale_spec)

    try:
        confirm_invoice("any-draft-id-doesnt-matter")
        assert False, "expected confirm_invoice to raise when requires_confirmation is stale"
    except RuntimeError as e:
        assert "requires_confirmation" in str(e)
