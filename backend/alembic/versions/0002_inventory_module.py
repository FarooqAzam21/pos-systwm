"""Add inventory entities for categories, suppliers, products and stock movements

Revision ID: 0002_inventory_module
Revises: 0001_initial
Create Date: 2026-10-06 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_inventory_module"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("business_id", "name", name="uq_categories_business_name"),
    )
    op.create_index("ix_categories_business_active", "categories", ["business_id", "is_active"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=False, server_default="pcs"),
        sa.Column("cost_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("selling_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("maximum_stock", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
        sa.UniqueConstraint("business_id", "barcode", name="uq_products_business_barcode"),
    )
    op.create_index("ix_products_business_active", "products", ["business_id", "is_active"], unique=False)
    op.create_index("ix_products_category_active", "products", ["category_id", "is_active"], unique=False)

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("tax_number", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_suppliers_business_active", "suppliers", ["business_id", "is_active"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.Enum("opening_stock", "purchase", "sale", "return", "adjustment_in", "adjustment_out", "damage", "transfer_in", "transfer_out", name="stock_movement_type"), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("previous_stock", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("new_stock", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_stock_movements_business_created_at", "stock_movements", ["business_id", "created_at"], unique=False)
    op.create_index("ix_stock_movements_product_created_at", "stock_movements", ["product_id", "created_at"], unique=False)
    op.create_index("ix_stock_movements_created_by", "stock_movements", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_by", table_name="stock_movements")
    op.drop_index("ix_stock_movements_product_created_at", table_name="stock_movements")
    op.drop_index("ix_stock_movements_business_created_at", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_suppliers_business_active", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_products_category_active", table_name="products")
    op.drop_index("ix_products_business_active", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_business_active", table_name="categories")
    op.drop_table("categories")
