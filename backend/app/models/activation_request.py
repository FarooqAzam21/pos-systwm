import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ActivationRequest(Base):
    __tablename__ = "activation_requests"
    __table_args__ = (
        Index("ix_activation_business_status", "business_id", "status", "created_at"),
        Index("ix_activation_user_status", "user_id", "status"),
        Index("uq_activation_open_user", "user_id", unique=True,
              postgresql_where=text("status IN ('pending_approval', 'otp_issued')"),
              sqlite_where=text("status IN ('pending_approval', 'otp_issued')")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_approval", server_default="pending_approval")
    otp_hmac: Mapped[str | None] = mapped_column(String(64))
    otp_encrypted: Mapped[str | None] = mapped_column(String(256))
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
