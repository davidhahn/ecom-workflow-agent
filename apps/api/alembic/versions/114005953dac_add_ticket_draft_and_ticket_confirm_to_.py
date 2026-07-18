"""add ticket_draft and ticket_confirm to request_log request_type

Revision ID: 114005953dac
Revises: 966f00ae6319
Create Date: 2026-07-18 16:11:38.773714

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '114005953dac'
down_revision: Union[str, Sequence[str], None] = '966f00ae6319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TYPES = "'sql','rag','analyze','refund_evaluate'"
NEW_TYPES = "'sql','rag','analyze','refund_evaluate','ticket_draft','ticket_confirm'"


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
