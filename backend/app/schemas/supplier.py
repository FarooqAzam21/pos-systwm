from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_email(value: str) -> str:
    text = value.strip().lower()
    if not text:
        return text
    if "@" not in text or text.count("@") != 1:
        raise ValueError("Email address is invalid")
    local, domain = text.split("@", 1)
    if not local or not domain:
        raise ValueError("Email address is invalid")
    if "." not in domain and "test" not in domain and "local" not in domain:
        raise ValueError("Email address is invalid")
    return text


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company_name: str | None = Field(default=None, max_length=160)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    tax_number: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return None if value is None else normalize_email(value)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    company_name: str | None = Field(default=None, max_length=160)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    tax_number: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class SupplierRead(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    company_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    tax_number: str | None
    notes: str | None
    is_active: bool
    outstanding_balance: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
