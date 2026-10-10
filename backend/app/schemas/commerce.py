from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.payment import PaymentMethod


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    tax_number: str | None = Field(default=None, max_length=80)
    credit_limit: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Customer name is required")
        return name


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    tax_number: str | None = Field(default=None, max_length=80)
    credit_limit: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class CustomerRead(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    tax_number: str | None
    credit_limit: Decimal
    current_balance: Decimal
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListRead(BaseModel):
    items: list[CustomerRead]
    total: int
    page: int
    limit: int


class PurchaseItemInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)


class PurchaseCreate(BaseModel):
    supplier_id: UUID
    invoice_number: str = Field(min_length=1, max_length=80)
    purchase_date: date | None = None
    discount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    paid_amount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    items: list[PurchaseItemInput] = Field(min_length=1)


class SaleItemInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)


class SaleCreate(BaseModel):
    customer_id: UUID | None = None
    new_customer: CustomerCreate | None = None
    discount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    paid_amount: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod = PaymentMethod.CASH
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    items: list[SaleItemInput] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class CustomerPaymentCreate(BaseModel):
    customer_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod
    payment_date: datetime | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class SupplierPaymentCreate(BaseModel):
    purchase_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod
    payment_date: datetime | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class ReturnItemInput(BaseModel):
    sale_item_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SaleReturnCreate(BaseModel):
    items: list[ReturnItemInput] = Field(min_length=1)
    payment_method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class SaleRead(BaseModel):
    id: UUID
    business_id: UUID
    invoice_number: str
    customer_id: UUID | None
    sale_date: datetime
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    payment_status: str
    cogs_amount: Decimal
    gross_profit: Decimal
    status: str
    created_by: UUID | None
    created_at: datetime
    customer_name: str | None = None
    cashier_name: str | None = None


class PaymentRead(BaseModel):
    id: UUID
    business_id: UUID
    payment_type: str
    reference_type: str
    reference_id: str
    customer_id: UUID | None
    amount: Decimal
    payment_method: str
    payment_date: datetime
    reference_number: str | None
    notes: str | None
    received_by: UUID | None
    created_at: datetime


class ReturnRead(BaseModel):
    id: UUID
    business_id: UUID
    sale_id: UUID
    refund_amount: Decimal
    notes: str | None
    created_by: UUID | None
    created_at: datetime
