"""Add customers, purchasing, sales, payments and returns.

Revision ID: 0003_purchasing_pos
Revises: 0002_inventory_module
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_purchasing_pos"
down_revision = "0002_inventory_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("email", sa.String(320)),
        sa.Column("address", sa.String(500)),
        sa.Column("city", sa.String(120)),
        sa.Column("tax_number", sa.String(80)),
        sa.Column("credit_limit", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("current_balance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("credit_limit >= 0 AND current_balance >= 0", name="ck_customers_balances_nonnegative"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_customers_business_id", "customers", ["business_id"])
    op.create_index("ix_customers_business_name", "customers", ["business_id", "name"])
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_email", "customers", ["email"])

    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(80), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("outstanding_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_status", sa.Enum("unpaid", "partial", "paid", name="purchase_payment_status"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("total_amount >= 0 AND paid_amount >= 0 AND outstanding_amount >= 0", name="ck_purchases_amounts_nonnegative"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("business_id", "invoice_number", name="uq_purchases_business_invoice"),
    )
    op.create_index("ix_purchases_business_id", "purchases", ["business_id"])
    op.create_index("ix_purchases_supplier_id", "purchases", ["supplier_id"])
    op.create_index("ix_purchases_business_date", "purchases", ["business_id", "purchase_date"])

    op.create_table(
        "purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_items_quantity_positive"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_purchase_items_business_id", "purchase_items", ["business_id"])
    op.create_index("ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"])
    op.create_index("ix_purchase_items_product_id", "purchase_items", ["product_id"])
    op.create_index("ix_purchase_items_business_product", "purchase_items", ["business_id", "product_id"])

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(80), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("sale_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("outstanding_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_status", sa.Enum("unpaid", "partial", "paid", name="sale_payment_status"), nullable=False),
        sa.Column("cogs_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_profit", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum("completed", "returned", "partially_returned", "voided", name="sale_status"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("total_amount >= 0 AND paid_amount >= 0 AND outstanding_amount >= 0", name="ck_sales_amounts_nonnegative"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("business_id", "invoice_number", name="uq_sales_business_invoice"),
    )
    op.create_index("ix_sales_business_id", "sales", ["business_id"])
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"])
    op.create_index("ix_sales_business_created_at", "sales", ["business_id", "created_at"])
    op.create_index("ix_sales_business_customer", "sales", ["business_id", "customer_id"])

    op.create_table(
        "sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("returned_quantity", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("cogs", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_profit", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_sale_items_business_id", "sale_items", ["business_id"])
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])
    op.create_index("ix_sale_items_business_product", "sale_items", ["business_id", "product_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_type", sa.Enum("incoming", "outgoing", name="payment_type"), nullable=False),
        sa.Column("reference_type", sa.Enum("sale", "purchase", "customer_payment", "supplier_payment", "refund", name="payment_reference_type"), nullable=False),
        sa.Column("reference_id", sa.String(64), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.Enum("cash", "card", "bank_transfer", "mobile_wallet", "other", name="payment_method"), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("notes", sa.Text()),
        sa.Column("received_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["received_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_payments_business_id", "payments", ["business_id"])
    op.create_index("ix_payments_reference_id", "payments", ["reference_id"])
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_business_date", "payments", ["business_id", "payment_date"])

    op.create_table(
        "sale_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sale_returns_business_id", "sale_returns", ["business_id"])
    op.create_index("ix_sale_returns_sale_id", "sale_returns", ["sale_id"])
    op.create_index("ix_sale_returns_business_date", "sale_returns", ["business_id", "created_at"])

    op.create_table(
        "sale_return_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("cogs", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_return_items_quantity_positive"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_id"], ["sale_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_sale_return_items_business_id", "sale_return_items", ["business_id"])
    op.create_index("ix_sale_return_items_return_id", "sale_return_items", ["return_id"])
    op.create_index("ix_sale_return_items_sale_item_id", "sale_return_items", ["sale_item_id"])
    op.create_index("ix_sale_return_items_product_id", "sale_return_items", ["product_id"])
    op.create_index("ix_sale_return_items_business_sale_item", "sale_return_items", ["business_id", "sale_item_id"])


def downgrade() -> None:
    op.drop_table("sale_return_items")
    op.drop_table("sale_returns")
    op.drop_table("payments")
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.drop_table("purchase_items")
    op.drop_table("purchases")
    op.drop_table("customers")
    for enum_name in (
        "payment_method",
        "payment_reference_type",
        "payment_type",
        "sale_status",
        "sale_payment_status",
        "purchase_payment_status",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
