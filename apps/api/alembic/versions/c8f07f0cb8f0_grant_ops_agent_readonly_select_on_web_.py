"""grant ops_agent_readonly select on web_analytics and campaigns

Revision ID: c8f07f0cb8f0
Revises: 8fb0658c0657
Create Date: 2026-07-25 10:32:49.127414

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'c8f07f0cb8f0'
down_revision: Union[str, Sequence[str], None] = '8fb0658c0657'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE = "ops_agent_readonly"

# Neither table has PII/sensitive columns (unlike customers.email), so a
# plain table-wide grant is correct here — no column-level restriction
# needed, matching the shipments grant pattern from
# 966f00ae6319_grant_ops_agent_readonly_select_on_shipments.py. Without
# this, layer 1 (ALLOWED_TABLES in app/query/constants.py) can permit a
# query against these tables, but layer 3 (the DB role itself) would still
# reject it at execution with a permission-denied error.


def upgrade() -> None:
    op.get_bind().execute(text(f"GRANT SELECT ON web_analytics, campaigns TO {ROLE}"))


def downgrade() -> None:
    op.get_bind().execute(text(f"REVOKE ALL ON web_analytics, campaigns FROM {ROLE}"))
