"""add policy_chunks table for RAG

Revision ID: b3d0b9eba18b
Revises: e226476acfd7
Create Date: 2026-07-08 19:59:36.638465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'b3d0b9eba18b'
down_revision: Union[str, Sequence[str], None] = 'e226476acfd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # No ANN index (ivfflat/hnsw): the corpus is ~17 rows, small and fixed.
    # An ANN index needs a meaningful amount of data to build useful
    # clusters and would just add complexity here — an exact sequential
    # scan with the `<=>` operator is both correct and fast at this size.
    # Reconsider if the corpus grows into the thousands.
    op.create_table('policy_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(1024), nullable=False),
    sa.Column('source_doc', sa.Text(), nullable=False),
    sa.Column('rule_number', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('policy_chunks')
    # Deliberately not dropping the vector extension — other features may
    # depend on it, and DROP EXTENSION would fail if they do anyway.
