from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseOrderItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expected_unit_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    expected_delivery_date: date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderStatusUpdate(BaseModel):
    status: Literal['ordered', 'cancelled']
