from datetime import datetime
from uuid import UUID

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_email(value: str) -> str:
    text = value.strip().lower()
    if "@" not in text or text.count("@") != 1:
        raise ValueError("Email address is invalid")
    local, domain = text.split("@", 1)
    if not local or not domain or "." not in domain:
        raise ValueError("Email address is invalid")
    return text


class BusinessUpdate(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    owner_name: str = Field(min_length=2, max_length=120)
    email: str
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    tax_number: str | None = Field(default=None, max_length=80)
    currency: str = Field(min_length=3, max_length=3)
    timezone: str = Field(min_length=1, max_length=64)
    invoice_prefix: str = Field(default="INV", min_length=1, max_length=20)
    invoice_footer: str | None = Field(default=None, max_length=500)
    logo: str | None = Field(default=None, max_length=2048)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error
        return value


class BusinessRead(BaseModel):
    id: UUID
    business_name: str
    owner_name: str
    email: str
    phone: str | None
    address: str | None
    city: str | None
    tax_number: str | None
    currency: str
    timezone: str
    invoice_prefix: str
    invoice_footer: str | None
    logo: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
