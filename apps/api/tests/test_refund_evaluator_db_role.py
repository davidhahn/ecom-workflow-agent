"""Fails if refund_evaluator stops using its restricted DB role."""

from sqlalchemy import text

from app.orchestrator import refund_evaluator

EXPECTED_ROLE = "refund_evaluator_readonly"


def test_refund_evaluator_session_uses_restricted_readonly_role():
    with refund_evaluator.SessionLocal() as session:
        current_user, current_role = session.execute(
            text("SELECT current_user, current_role")
        ).one()

    assert current_user == EXPECTED_ROLE
    assert current_role == EXPECTED_ROLE
