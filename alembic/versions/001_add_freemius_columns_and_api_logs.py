"""add freemius columns and api_logs table

Revision ID: 001
Revises: None
Create Date: 2026-03-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Freemius columns to accounts table.
    op.add_column("accounts", sa.Column("freemius_user_id", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("freemius_plan_id", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("license_key", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_accounts_freemius_user_id", "accounts", ["freemius_user_id"])

    # Create api_logs table.
    op.create_table(
        "api_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("api_logs")
    op.drop_constraint("uq_accounts_freemius_user_id", "accounts", type_="unique")
    op.drop_column("accounts", "plan_expires_at")
    op.drop_column("accounts", "license_key")
    op.drop_column("accounts", "freemius_plan_id")
    op.drop_column("accounts", "freemius_user_id")
