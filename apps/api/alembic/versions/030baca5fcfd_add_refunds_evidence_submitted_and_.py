"""add refunds.evidence_submitted and products category check

Revision ID: 030baca5fcfd
Revises: b3d0b9eba18b
Create Date: 2026-07-08 20:46:05.854134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '030baca5fcfd'
down_revision: Union[str, Sequence[str], None] = 'b3d0b9eba18b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('refunds', sa.Column('evidence_submitted', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # Alembic's autogenerate doesn't detect CHECK constraints, so this half
    # is hand-written. Category list matches what's actually in seed.py's
    # PRODUCT_ROWS (Electronics, Apparel, Home, Grocery, Office) plus the
    # two new values (Clearance, Final Sale) — verified against the live DB
    # before writing this migration, not assumed.
    op.create_check_constraint(
        'category_check',
        'products',
        "category IN ('Electronics','Apparel','Home','Grocery','Office','Clearance','Final Sale')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('category_check', 'products', type_='check')
    op.drop_column('refunds', 'evidence_submitted')
