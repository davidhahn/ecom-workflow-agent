"""add llm_latency_ms to request_log

Revision ID: 873e07c9f3aa
Revises: f3a1c9d02b47
Create Date: 2026-08-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '873e07c9f3aa'
down_revision: Union[str, Sequence[str], None] = 'f3a1c9d02b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("request_log", sa.Column("llm_latency_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_log", "llm_latency_ms")
