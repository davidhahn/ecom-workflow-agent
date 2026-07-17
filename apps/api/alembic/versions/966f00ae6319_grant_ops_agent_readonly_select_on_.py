"""grant ops_agent_readonly select on shipments

Revision ID: 966f00ae6319
Revises: 3f4300144152
Create Date: 2026-07-17 16:37:28.975662

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '966f00ae6319'
down_revision: Union[str, Sequence[str], None] = '3f4300144152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE = "ops_agent_readonly"

# shipments has no PII/sensitive columns (unlike customers.email), so a
# plain table-wide grant is correct here — no column-level restriction
# needed, matching the NON_CUSTOMER_TABLES grant pattern from
# e226476acfd7_create_ops_agent_readonly_role_with_.py.


def upgrade() -> None:
    op.get_bind().execute(text(f"GRANT SELECT ON shipments TO {ROLE}"))


def downgrade() -> None:
    op.get_bind().execute(text(f"REVOKE ALL ON shipments FROM {ROLE}"))
