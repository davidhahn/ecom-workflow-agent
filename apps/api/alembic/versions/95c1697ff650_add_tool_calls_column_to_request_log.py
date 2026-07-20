"""add tool_calls column to request_log

Revision ID: 95c1697ff650
Revises: c559d79fb246
Create Date: 2026-07-19 20:16:57.254246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '95c1697ff650'
down_revision: Union[str, Sequence[str], None] = 'c559d79fb246'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'request_log',
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('request_log', 'tool_calls')
