"""create refund_evaluator_readonly role with restricted grants

Revision ID: 26533063b44f
Revises: c8f07f0cb8f0
Create Date: 2026-08-06 00:00:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '26533063b44f'
down_revision: Union[str, Sequence[str], None] = 'c8f07f0cb8f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE = "refund_evaluator_readonly"

# Narrower than the default app connection (no write access, no other
# tables) but broader than ops_agent_readonly on one specific point:
# customers.email is granted here. refund_evaluator.resolve_order_item()
# matches a customer by name OR email extracted from the request text -
# unlike the SQL query path, that email is only ever used as an internal
# WHERE-clause comparison and never appears in a response, so it doesn't
# carry the same leak risk ops_agent_readonly's column exclusion guards
# against. See ARCHITECTURE.md's "PII column-scoping is partial" note and
# DECISIONS.md for the tradeoff.
TABLES = ("customers", "orders", "order_items", "products", "refunds")


def _require_password() -> str:
    try:
        return os.environ["REFUND_EVALUATOR_DB_PASSWORD"]
    except KeyError:
        raise RuntimeError(
            "REFUND_EVALUATOR_DB_PASSWORD must be set before running this "
            "migration (it becomes the refund_evaluator_readonly Postgres "
            "role's password)."
        ) from None


def upgrade() -> None:
    password = _require_password()
    conn = op.get_bind()
    dbname = conn.engine.url.database

    # Same inlining rationale as e226476acfd7: CREATE/ALTER ROLE ... PASSWORD
    # takes a literal, not a bind parameter, and the value is an
    # operator-supplied env var read at migration-run time, not attacker
    # input.
    escaped_password = password.replace("'", "''")

    role_exists = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": ROLE}
    ).scalar()
    if role_exists:
        conn.execute(text(f"ALTER ROLE {ROLE} WITH LOGIN PASSWORD '{escaped_password}'"))
    else:
        conn.execute(text(f"CREATE ROLE {ROLE} WITH LOGIN PASSWORD '{escaped_password}'"))

    conn.execute(text(f'GRANT CONNECT ON DATABASE "{dbname}" TO {ROLE}'))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {ROLE}"))

    tables = ", ".join(TABLES)
    conn.execute(text(f"GRANT SELECT ON {tables} TO {ROLE}"))

    # Same backstops as ops_agent_readonly: a hard statement timeout
    # independent of any application-level timeout, and read-only at the
    # transaction level so even a query that slipped past application logic
    # cannot write.
    conn.execute(text(f"ALTER ROLE {ROLE} SET statement_timeout = '5000'"))
    conn.execute(text(f"ALTER ROLE {ROLE} SET default_transaction_read_only = on"))


def downgrade() -> None:
    conn = op.get_bind()
    dbname = conn.engine.url.database

    tables = ", ".join(TABLES)
    conn.execute(text(f"REVOKE ALL ON {tables} FROM {ROLE}"))
    conn.execute(text(f"REVOKE USAGE ON SCHEMA public FROM {ROLE}"))
    conn.execute(text(f'REVOKE CONNECT ON DATABASE "{dbname}" FROM {ROLE}'))
    conn.execute(text(f"DROP ROLE IF EXISTS {ROLE}"))
