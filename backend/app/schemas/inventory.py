from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventorySummary(BaseModel):
    total_products: int
    inventory_value: Decimal
    low_stock: int
    out_of_stock: int
    total_stock_units: Decimal
    category_count: int


class LowStockItem(BaseModel):
    id: UUID
    sku: str
    name: str
    current_stock: Decimal
    minimum_stock: Decimal
    required_quantity: Decimal
    supplier_name: str | None = None
    stock_status: str
    inventory_value: Decimal


class ProductMovementRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None = None
    movement_type: str
    quantity: str
    previous_stock: str
    new_stock: str
    unit_cost: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    notes: str | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductAdjustmentRequest(BaseModel):
    movement_type: str = Field(pattern="^(adjustment_in|adjustment_out)$")
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)


class OpeningStockRequest(BaseModel):
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)


class ProductListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    limit: int
