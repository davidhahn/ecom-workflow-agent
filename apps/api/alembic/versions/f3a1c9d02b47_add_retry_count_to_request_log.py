"""add retry_count to request_log

Revision ID: f3a1c9d02b47
Revises: 00de3e24bd8d
Create Date: 2026-08-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9d02b47'
down_revision: Union[str, Sequence[str], None] = '00de3e24bd8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("request_log", sa.Column("retry_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_log", "retry_count")
