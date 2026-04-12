"""add community features — submission, voting, moderation

Revision ID: 002
Revises: 001
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add community columns to images table.
    op.add_column("images", sa.Column("community_status", sa.String(20), nullable=True))
    op.add_column("images", sa.Column("community_votes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("images", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))

    # Create community_votes table.
    op.create_table(
        "community_votes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("image_id", "account_id", name="uq_community_vote"),
    )


def downgrade() -> None:
    op.drop_table("community_votes")
    op.drop_column("images", "submitted_at")
    op.drop_column("images", "community_votes")
    op.drop_column("images", "community_status")
