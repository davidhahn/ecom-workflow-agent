"""add prompt_version to query_audit_log

Revision ID: 00de3e24bd8d
Revises: 26533063b44f
Create Date: 2026-08-10 18:21:44.386808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00de3e24bd8d'
down_revision: Union[str, Sequence[str], None] = '26533063b44f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("query_audit_log", sa.Column("prompt_version", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_audit_log", "prompt_version")
