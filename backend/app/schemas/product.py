from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductBase(BaseModel):
    category_id: UUID | None = None
    sku: str = Field(min_length=1, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=1000)
    brand: str | None = Field(default=None, max_length=120)
    unit: str = Field(default="pcs", min_length=1, max_length=40)
    cost_price: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    minimum_stock: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    maximum_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool = True
    opening_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @field_validator("sku", "name", "unit")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class ProductCreate(ProductBase):
    unit: str = Field(min_length=1, max_length=40)
    cost_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    opening_stock: Decimal = Field(ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def validate_stock_limits(self):
        if self.maximum_stock is not None and self.maximum_stock < self.minimum_stock:
            raise ValueError("Maximum stock must be greater than or equal to minimum stock")
        return self


class ProductUpdate(ProductBase):
    category_id: UUID | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=1000)
    brand: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    minimum_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    maximum_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None
    opening_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ProductRead(BaseModel):
    id: UUID
    business_id: UUID
    category_id: UUID | None
    category_name: str | None = None
    sku: str
    barcode: str | None
    name: str
    description: str | None
    brand: str | None
    unit: str
    cost_price: Decimal
    selling_price: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    maximum_stock: Decimal | None
    is_active: bool
    inventory_value: Decimal
    stock_status: str
    unit_profit: Decimal
    margin_percentage: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
