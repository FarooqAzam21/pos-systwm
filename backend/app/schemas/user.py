from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime

from app.models.user import UserRole
from app.schemas.auth import normalize_email, validate_strong_password


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.CASHIER

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr) -> str:
        email = normalize_email(value)
        if email.rsplit("@", 1)[-1] != "gmail.com":
            raise ValueError("Staff username must be a Gmail address")
        return email

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        email = normalize_email(value)
        if email.rsplit("@", 1)[-1] != "gmail.com":
            raise ValueError("Staff username must be a Gmail address")
        return email


class StaffRead(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    is_activated: bool
    must_change_password: bool
    last_login_at: datetime | None


class TemporaryPasswordRead(BaseModel):
    temporary_password: str
    message: str = "Share this password directly with the staff member. It will be required once and must be changed."
