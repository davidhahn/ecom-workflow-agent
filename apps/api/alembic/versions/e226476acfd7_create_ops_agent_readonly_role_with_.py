"""create ops_agent_readonly role with restricted grants

Revision ID: e226476acfd7
Revises: bc4f536077fe
Create Date: 2026-07-07 20:02:31.662495

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'e226476acfd7'
down_revision: Union[str, Sequence[str], None] = 'bc4f536077fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE = "ops_agent_readonly"

# customers is handled separately with column-level grants (below) because
# Postgres table-level and column-level SELECT are independent ACL entries —
# REVOKE SELECT (email) is a no-op on a role that already has table-wide
# SELECT, so email must never be included in a table-level GRANT in the
# first place.
NON_CUSTOMER_TABLES = (
    "products",
    "orders",
    "order_items",
    "refunds",
    "support_tickets",
)
CUSTOMER_VISIBLE_COLUMNS = ("id", "name", "region", "created_at")


def _require_password() -> str:
    try:
        return os.environ["OPS_AGENT_DB_PASSWORD"]
    except KeyError:
        raise RuntimeError(
            "OPS_AGENT_DB_PASSWORD must be set before running this migration "
            "(it becomes the ops_agent_readonly Postgres role's password)."
        ) from None


def upgrade() -> None:
    password = _require_password()
    conn = op.get_bind()
    dbname = conn.engine.url.database

    # CREATE ROLE / ALTER ROLE ... PASSWORD takes a literal, not a bind
    # parameter — Postgres's grammar for this clause doesn't accept $1.
    # Safe to inline here: the password is an operator-supplied env var read
    # at migration-run time, not attacker input.
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

    tables = ", ".join(NON_CUSTOMER_TABLES)
    conn.execute(text(f"GRANT SELECT ON {tables} TO {ROLE}"))

    # Layer 3 backstop: customers.email is never granted, at the column
    # level, so this holds even if layers 1-2 have a bug and let a query
    # select it. (Column-level GRANT, not table-level GRANT + column REVOKE
    # — see note above.)
    columns = ", ".join(CUSTOMER_VISIBLE_COLUMNS)
    conn.execute(text(f"GRANT SELECT ({columns}) ON customers TO {ROLE}"))

    # Hard timeout backstop, independent of any application-level timeout.
    conn.execute(text(f"ALTER ROLE {ROLE} SET statement_timeout = '5000'"))

    # Extra defense in depth: even a query that slipped past the SELECT-only
    # AST check (layer 1) cannot write, because the role's sessions are
    # read-only at the transaction level.
    conn.execute(text(f"ALTER ROLE {ROLE} SET default_transaction_read_only = on"))


def downgrade() -> None:
    conn = op.get_bind()
    dbname = conn.engine.url.database

    tables = ", ".join(NON_CUSTOMER_TABLES)
    conn.execute(text(f"REVOKE ALL ON {tables} FROM {ROLE}"))
    columns = ", ".join(CUSTOMER_VISIBLE_COLUMNS)
    conn.execute(text(f"REVOKE SELECT ({columns}) ON customers FROM {ROLE}"))
    conn.execute(text(f"REVOKE USAGE ON SCHEMA public FROM {ROLE}"))
    conn.execute(text(f'REVOKE CONNECT ON DATABASE "{dbname}" FROM {ROLE}'))
    conn.execute(text(f"DROP ROLE IF EXISTS {ROLE}"))
