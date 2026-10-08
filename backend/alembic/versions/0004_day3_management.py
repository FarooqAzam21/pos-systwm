"""Add Day 3 expenses, audit logs and business settings.

Revision ID: 0004_day3_management
Revises: 0003_purchasing_pos
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_day3_management"
down_revision = "0003_purchasing_pos"
branch_labels = None
depends_on = None

payment_method = postgresql.ENUM(
    "cash",
    "card",
    "bank_transfer",
    "mobile_wallet",
    "other",
    name="payment_method",
    create_type=False,
)


def upgrade() -> None:
    op.add_column("businesses", sa.Column("city", sa.String(120), nullable=True))
    op.add_column("businesses", sa.Column("tax_number", sa.String(80), nullable=True))
    op.add_column(
        "businesses",
        sa.Column("invoice_prefix", sa.String(20), server_default="INV", nullable=False),
    )
    op.add_column("businesses", sa.Column("invoice_footer", sa.String(500), nullable=True))

    op.create_table(
        "expense_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "name", name="uq_expense_categories_business_name"),
    )
    op.create_index("ix_expense_categories_business_id", "expense_categories", ["business_id"])
    op.create_index("ix_expense_categories_business_active", "expense_categories", ["business_id", "is_active"])

    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_business_id", "expenses", ["business_id"])
    op.create_index("ix_expenses_category_id", "expenses", ["category_id"])
    op.create_index("ix_expenses_business_date", "expenses", ["business_id", "expense_date"])
    op.create_index("ix_expenses_created_by", "expenses", ["created_by"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_business_id", "audit_logs", ["business_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_business_created", "audit_logs", ["business_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_business_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_business_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_expenses_created_by", table_name="expenses")
    op.drop_index("ix_expenses_business_date", table_name="expenses")
    op.drop_index("ix_expenses_category_id", table_name="expenses")
    op.drop_index("ix_expenses_business_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_expense_categories_business_active", table_name="expense_categories")
    op.drop_index("ix_expense_categories_business_id", table_name="expense_categories")
    op.drop_table("expense_categories")
    op.drop_column("businesses", "invoice_footer")
    op.drop_column("businesses", "invoice_prefix")
    op.drop_column("businesses", "tax_number")
    op.drop_column("businesses", "city")
