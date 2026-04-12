"""add account role column

Revision ID: 003
Revises: 001
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("accounts", "role")
