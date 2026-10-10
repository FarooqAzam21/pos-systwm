import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("business_id", "order_number", name="uq_purchase_orders_business_number"),
        UniqueConstraint("purchase_id", name="uq_purchase_orders_purchase"),
        CheckConstraint("status IN ('draft', 'ordered', 'received', 'cancelled')", name="ck_purchase_orders_status"),
        Index("ix_purchase_orders_business_created", "business_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="SET NULL"))
    order_number: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_order_items_quantity_positive"),
        CheckConstraint("expected_unit_cost >= 0", name="ck_purchase_order_items_cost_nonnegative"),
        Index("ix_purchase_order_items_business_product", "business_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expected_unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[PurchaseOrder] = relationship(back_populates="items")
