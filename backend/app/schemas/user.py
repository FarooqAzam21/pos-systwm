from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole
from app.schemas.auth import normalize_email, validate_strong_password


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.CASHIER

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return normalize_email(value) if value is not None else None
