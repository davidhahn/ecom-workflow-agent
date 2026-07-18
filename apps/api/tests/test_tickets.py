"""Tests for the two-call draft/confirm support-ticket write flow — the
first genuine write path in the system. Exercises real Postgres (no mocks),
consistent with this project's established testing style."""

import dataclasses
import time

from sqlalchemy import func, select

from app.db.models import SupportTicket
from app.db.session import SessionLocal
from app.tickets.draft_store import create_draft
from app.tickets.service import confirm_ticket, draft_ticket
from app.tools.registry import TOOLS

# A real seeded customer (see apps/api/app/db/seed.py) with no product
# reference needed — keeps these tests independent of resolve_order_item's
# product-matching behavior, which is exercised separately below.
_REAL_CUSTOMER = "James O'Brien"


def _support_ticket_count() -> int:
    with SessionLocal() as session:
        return session.execute(select(func.count(SupportTicket.id))).scalar_one()


def test_draft_does_not_write_to_support_tickets():
    before = _support_ticket_count()

    result = draft_ticket(
        f"Hi, this is {_REAL_CUSTOMER}. I was charged twice for my last order, "
        "can you look into it? (draft-no-write test, unique phrasing)"
    )

    assert result.status == "drafted"
    assert result.draft_id is not None
    assert _support_ticket_count() == before


def test_confirm_writes_exactly_once_not_duplicated_on_retry():
    before = _support_ticket_count()

    draft = draft_ticket(
        f"Hi, this is {_REAL_CUSTOMER}. My package shows delivered but never arrived. "
        "(confirm-once test, unique phrasing)"
    )
    assert draft.status == "drafted"

    first_confirm = confirm_ticket(draft.draft_id)
    assert first_confirm.status == "created"
    assert first_confirm.ticket_id is not None
    assert _support_ticket_count() == before + 1

    second_confirm = confirm_ticket(draft.draft_id)
    assert second_confirm.status == "created"
    assert second_confirm.ticket_id == first_confirm.ticket_id
    assert _support_ticket_count() == before + 1  # still +1, not +2

    # Field values actually match what was resolved/extracted, not just the
    # status codes.
    with SessionLocal() as session:
        row = session.get(SupportTicket, first_confirm.ticket_id)
    assert row is not None
    assert str(row.customer_id) == str(draft.customer_id)
    assert row.category == draft.category
    assert row.description == draft.description


def test_confirm_with_missing_draft_id_returns_clear_error():
    result = confirm_ticket("this-draft-id-was-never-created")
    assert result.status == "error"
    assert result.error_reason is not None
    assert result.ticket_id is None


def test_confirm_with_expired_draft_returns_clear_error():
    draft_id = create_draft(
        {
            "customer_id": None,
            "order_id": None,
            "product_id": None,
            "category": "other",
            "description": "irrelevant - should never be read, draft expires first",
        },
        ttl_seconds=0.01,
    )
    time.sleep(0.05)

    result = confirm_ticket(draft_id)
    assert result.status == "error"
    assert result.error_reason is not None


def test_draft_unresolvable_customer_returns_could_not_process():
    result = draft_ticket(
        "Hi, this is Zzyzx Nonexistent Customer, product totally not in the "
        "catalog is broken. (unresolvable-customer test, unique phrasing)"
    )
    assert result.status == "could_not_process"
    assert result.draft_id is None
    assert result.reasoning is not None


def test_confirm_enforces_requires_confirmation_flag(monkeypatch):
    """Proves the gate is actually read and enforced at call time, not just
    declared on the ToolSpec — flipping the flag changes real behavior."""
    stale_spec = dataclasses.replace(TOOLS["draft_support_ticket"], requires_confirmation=False)
    monkeypatch.setitem(TOOLS, "draft_support_ticket", stale_spec)

    try:
        confirm_ticket("any-draft-id-doesnt-matter")
        assert False, "expected confirm_ticket to raise when requires_confirmation is stale"
    except RuntimeError as e:
        assert "requires_confirmation" in str(e)
