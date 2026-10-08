import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
        UniqueConstraint("business_id", "barcode", name="uq_products_business_barcode"),
        Index("ix_products_business_active", "business_id", "is_active"),
        Index("ix_products_category_active", "category_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    brand: Mapped[str | None] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="pcs")
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_stock: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    minimum_stock: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    maximum_stock: Mapped[float | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(back_populates="products")
    category: Mapped["Category | None"] = relationship(back_populates="products")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="product")
