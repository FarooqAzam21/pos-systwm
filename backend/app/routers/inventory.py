from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import Permission, get_current_user, require_permission
from app.models.category import Category
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventorySummary,
    LowStockItem,
    OpeningStockRequest,
    ProductAdjustmentRequest,
    ProductMovementRead,
)
from app.services.inventory import apply_stock_change, inventory_value_for, stock_status_for
from app.services.audit import record_audit

router = APIRouter(prefix="/inventory", tags=["Inventory"])
INVENTORY_MANAGERS = (UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)


def decimal_to_string(value):
    if value is None:
        return None
    normalized = Decimal(str(value)).quantize(Decimal("0.01"))
    text = format(normalized.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@router.get("", response_model=InventorySummary)
def inventory_summary(
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    products = db.scalars(
        select(Product).where(
            Product.business_id == user.business_id,
            Product.is_active.is_(True),
        )
    ).all()
    low_stock_count = sum(
        1 for product in products if product.current_stock > 0 and product.current_stock <= product.minimum_stock
    )
    out_of_stock_count = sum(1 for product in products if product.current_stock == 0)
    total_stock_units = sum(Decimal(str(product.current_stock)) for product in products)
    inventory_value = sum(inventory_value_for(product) for product in products)
    return {
        "total_products": len(products),
        "inventory_value": Decimal(str(inventory_value)),
        "low_stock": low_stock_count,
        "out_of_stock": out_of_stock_count,
        "total_stock_units": Decimal(str(total_stock_units)),
        "category_count": db.scalar(
            select(func.count(Category.id)).where(Category.business_id == user.business_id)
        )
        or 0,
    }


@router.get("/low-stock", response_model=list[LowStockItem])
def low_stock(
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> list[dict]:
    products = db.scalars(
        select(Product).where(
            Product.business_id == user.business_id,
            Product.is_active.is_(True),
            Product.current_stock > 0,
            Product.current_stock <= Product.minimum_stock,
        )
    ).all()
    items = []
    for product in products:
        required = Decimal(str(product.minimum_stock)) - Decimal(str(product.current_stock))
        if required <= 0:
            required = Decimal("0")
        items.append(
            {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "current_stock": Decimal(str(product.current_stock)),
                "minimum_stock": Decimal(str(product.minimum_stock)),
                "required_quantity": Decimal(str(required)),
                "supplier_name": None,
                "stock_status": stock_status_for(product.current_stock, product.minimum_stock),
                "inventory_value": inventory_value_for(product),
            }
        )
    return items


@router.get("/out-of-stock", response_model=list[dict])
def out_of_stock_products(
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> list[dict]:
    products = db.scalars(
        select(Product).where(
            Product.business_id == user.business_id,
            Product.is_active.is_(True),
            Product.current_stock == 0,
        )
    ).all()
    return [
        {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "current_stock": Decimal(str(product.current_stock)),
            "minimum_stock": Decimal(str(product.minimum_stock)),
            "stock_status": stock_status_for(product.current_stock, product.minimum_stock),
            "inventory_value": inventory_value_for(product),
        }
        for product in products
    ]


@router.get("/{product_id}/movements", response_model=list[ProductMovementRead])
def list_product_movements(
    product_id: UUID,
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> list[StockMovement]:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == user.business_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    movements = db.scalars(
        select(StockMovement)
        .where(
            StockMovement.product_id == product_id,
            StockMovement.business_id == user.business_id,
        )
        .order_by(StockMovement.created_at.desc())
    ).all()
    results = []
    for movement in movements:
        creator = movement.creator
        quantity = str(Decimal(str(movement.quantity)).quantize(Decimal("0.01")))
        previous = str(Decimal(str(movement.previous_stock)).quantize(Decimal("0.01")))
        new_value = str(Decimal(str(movement.new_stock)).quantize(Decimal("0.01")))
        unit_cost = (
            str(Decimal(str(movement.unit_cost)).quantize(Decimal("0.01")))
            if movement.unit_cost is not None
            else None
        )
        results.append(
            {
                "id": movement.id,
                "product_id": movement.product_id,
                "product_name": product.name,
                "movement_type": movement.movement_type.value,
                "quantity": quantity,
                "previous_stock": previous,
                "new_stock": new_value,
                "unit_cost": unit_cost,
                "reference_type": movement.reference_type,
                "reference_id": movement.reference_id,
                "notes": movement.notes,
                "created_by": movement.created_by,
                "created_by_name": creator.name if creator else None,
                "created_at": movement.created_at,
            }
        )
    return results


@router.post("/{product_id}/opening-stock", response_model=ProductMovementRead)
def create_opening_stock(
    product_id: UUID,
    payload: OpeningStockRequest,
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductMovementRead:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == user.business_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    if product.current_stock > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opening stock can only be set for a product that has not started with stock",
        )
    quantity = Decimal(str(payload.quantity))
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opening stock quantity must be greater than zero",
        )
    movement = StockMovement(
        business_id=user.business_id,
        product_id=product.id,
        movement_type=MovementType.OPENING_STOCK,
        quantity=quantity,
        previous_stock=Decimal("0"),
        new_stock=quantity,
        unit_cost=payload.unit_cost or product.cost_price,
        reference_type="opening_stock",
        reference_id=str(product.id),
        notes=payload.notes or "Opening stock",
        created_by=user.id,
    )
    product.current_stock = quantity
    if payload.unit_cost is not None:
        product.cost_price = Decimal(str(payload.unit_cost))
    db.add(movement)
    record_audit(
        db, user.business_id, user.id, "adjust", "stock",
        product.id, f"Adjusted stock for {product.name} by {quantity * multiplier}",
    )
    db.commit()
    db.refresh(product)
    db.refresh(movement)
    return {
        "id": movement.id,
        "product_id": product.id,
        "product_name": product.name,
        "movement_type": movement.movement_type.value,
        "quantity": decimal_to_string(movement.quantity),
        "previous_stock": decimal_to_string(movement.previous_stock),
        "new_stock": decimal_to_string(movement.new_stock),
        "unit_cost": decimal_to_string(movement.unit_cost) if movement.unit_cost is not None else None,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "notes": movement.notes,
        "created_by": movement.created_by,
        "created_by_name": user.name,
        "created_at": movement.created_at,
    }


@router.post("/{product_id}/adjust", response_model=ProductMovementRead)
def adjust_inventory(
    product_id: UUID,
    payload: ProductAdjustmentRequest,
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == user.business_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    if payload.movement_type == "adjustment_in":
        multiplier = 1
    else:
        multiplier = -1
    quantity = Decimal(str(payload.quantity))
    previous_stock = Decimal(str(product.current_stock))
    new_stock = previous_stock + (quantity * multiplier)
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory cannot go below zero",
        )
    product.current_stock = new_stock
    movement = StockMovement(
        business_id=user.business_id,
        product_id=product.id,
        movement_type=MovementType(payload.movement_type),
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        unit_cost=payload.unit_cost or product.cost_price,
        reference_type="adjustment",
        reference_id=str(product.id),
        notes=payload.notes or "Stock adjustment",
        created_by=user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(product)
    db.refresh(movement)
    return {
        "id": movement.id,
        "product_id": product.id,
        "product_name": product.name,
        "movement_type": movement.movement_type.value,
        "quantity": decimal_to_string(movement.quantity),
        "previous_stock": decimal_to_string(movement.previous_stock),
        "new_stock": decimal_to_string(movement.new_stock),
        "unit_cost": decimal_to_string(movement.unit_cost) if movement.unit_cost is not None else None,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "notes": movement.notes,
        "created_by": movement.created_by,
        "created_by_name": user.name,
        "created_at": movement.created_at,
    }
