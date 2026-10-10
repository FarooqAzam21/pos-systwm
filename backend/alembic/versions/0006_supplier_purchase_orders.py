"""Track supplier orders before receipt."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_supplier_purchase_orders"
down_revision = "0005_daily_closings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_number", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("business_id", "order_number", name="uq_purchase_orders_business_number"),
        sa.UniqueConstraint("purchase_id", name="uq_purchase_orders_purchase"),
        sa.CheckConstraint("status IN ('draft', 'ordered', 'received', 'cancelled')", name="ck_purchase_orders_status"),
    )
    op.create_index("ix_purchase_orders_business_id", "purchase_orders", ["business_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_business_created", "purchase_orders", ["business_id", "created_at"])
    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("expected_unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_order_items_quantity_positive"),
        sa.CheckConstraint("expected_unit_cost >= 0", name="ck_purchase_order_items_cost_nonnegative"),
    )
    for col in ("business_id", "purchase_order_id", "product_id"):
        op.create_index(f"ix_purchase_order_items_{col}", "purchase_order_items", [col])
    op.create_index("ix_purchase_order_items_business_product", "purchase_order_items", ["business_id", "product_id"])


def downgrade() -> None:
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
