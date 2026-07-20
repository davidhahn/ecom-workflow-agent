"""add invoice_draft and invoice_confirm to request_log request_type

Revision ID: c559d79fb246
Revises: 533e0869fe06
Create Date: 2026-07-19 14:10:20.357659

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c559d79fb246'
down_revision: Union[str, Sequence[str], None] = '533e0869fe06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TYPES = "'sql','rag','analyze','refund_evaluate','ticket_draft','ticket_confirm'"
NEW_TYPES = (
    "'sql','rag','analyze','refund_evaluate','ticket_draft','ticket_confirm',"
    "'invoice_draft','invoice_confirm'"
)


def upgrade() -> None:
    op.drop_constraint("request_log_request_type_check", "request_log", type_="check")
    op.create_check_constraint(
        "request_log_request_type_check",
        "request_log",
        f"request_type IN ({NEW_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("request_log_request_type_check", "request_log", type_="check")
    op.create_check_constraint(
        "request_log_request_type_check",
        "request_log",
        f"request_type IN ({OLD_TYPES})",
    )
