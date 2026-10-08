"""Persist daily cash closing records.

Revision ID: 0005_daily_closings
Revises: 0004_day3_management
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_daily_closings"
down_revision = "0004_day3_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_closings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closing_date", sa.Date(), nullable=False),
        sa.Column("opening_cash", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("actual_closing_cash", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "closing_date", name="uq_daily_closings_business_date"),
    )
    op.create_index("ix_daily_closings_business_date", "daily_closings", ["business_id", "closing_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_closings_business_date", table_name="daily_closings")
    op.drop_table("daily_closings")
