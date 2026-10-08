from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentMethod


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class ExpenseCategoryRead(BaseModel):
    id: UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    category_id: UUID
    description: str = Field(min_length=2, max_length=240)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expense_date: date
    payment_method: PaymentMethod
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class ExpenseUpdate(BaseModel):
    category_id: UUID | None = None
    description: str | None = Field(default=None, min_length=2, max_length=240)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expense_date: date | None = None
    payment_method: PaymentMethod | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class ExpenseRead(BaseModel):
    id: UUID
    category_id: UUID
    category_name: str
    description: str
    amount: Decimal
    expense_date: date
    payment_method: PaymentMethod
    reference_number: str | None
    notes: str | None
    created_by: UUID | None
    created_by_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
