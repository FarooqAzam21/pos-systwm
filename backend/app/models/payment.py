import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PaymentType(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_WALLET = "mobile_wallet"
    OTHER = "other"


PAYMENT_METHOD_ENUM = Enum(
    PaymentMethod,
    name="payment_method",
    values_callable=lambda enum_type: [item.value for item in enum_type],
)


class PaymentReferenceType(str, enum.Enum):
    SALE = "sale"
    PURCHASE = "purchase"
    CUSTOMER_PAYMENT = "customer_payment"
    SUPPLIER_PAYMENT = "supplier_payment"
    REFUND = "refund"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_business_date", "business_id", "payment_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type", values_callable=lambda enum_type: [item.value for item in enum_type]),
        nullable=False,
    )
    reference_type: Mapped[PaymentReferenceType] = mapped_column(
        Enum(PaymentReferenceType, name="payment_reference_type", values_callable=lambda enum_type: [item.value for item in enum_type]),
        nullable=False,
    )
    reference_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(PAYMENT_METHOD_ENUM, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    received_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
