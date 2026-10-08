from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


def normalize_email(value: str) -> str:
    text = value.strip().lower()
    if "@" not in text or text.count("@") != 1:
        raise ValueError("Email address is invalid")
    local, domain = text.split("@", 1)
    if not local or not domain or "." not in domain:
        raise ValueError("Email address is invalid")
    return text


def validate_strong_password(value: str) -> str:
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must include at least one number")
    if not re.search(r"[^A-Za-z0-9\s]", value):
        raise ValueError("Password must include at least one special character")
    return value


class RegisterRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    owner_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_strong_password(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class UserRead(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    business_id: UUID
    business_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AccountUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("new_password")
    @classmethod
    def strong_new_password(cls, value: str | None) -> str | None:
        return validate_strong_password(value) if value is not None else None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: str
