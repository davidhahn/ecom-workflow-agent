"""add vendor_invoices table

Revision ID: 533e0869fe06
Revises: 114005953dac
Create Date: 2026-07-19 14:10:07.555092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '533e0869fe06'
down_revision: Union[str, Sequence[str], None] = '114005953dac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('vendor_invoices',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('vendor_name', sa.Text(), nullable=False),
    sa.Column('invoice_number', sa.Text(), nullable=False),
    sa.Column('invoice_date', sa.Date(), nullable=False),
    sa.Column('subtotal_cents', sa.Integer(), nullable=False),
    sa.Column('tax_cents', sa.Integer(), nullable=False),
    sa.Column('total_cents', sa.Integer(), nullable=False),
    sa.Column('line_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('field_confidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('flagged_reasons', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('validated','flagged','duplicate')", name='vendor_invoices_status_check'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_vendor_invoices_vendor_name_invoice_number',
        'vendor_invoices',
        ['vendor_name', 'invoice_number'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_vendor_invoices_vendor_name_invoice_number', table_name='vendor_invoices')
    op.drop_table('vendor_invoices')
