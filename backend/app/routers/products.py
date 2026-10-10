from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.category import Category
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.audit import record_audit
from app.services.inventory import (
    inventory_value_for,
    margin_percentage_for,
    product_stock_status,
    unit_profit_for,
)

router = APIRouter(prefix="/products", tags=["Products"])


def serialize_decimal(value):
    if value is None:
        return None
    text = str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def serialize_product(product: Product, *, include_cost_details: bool = True) -> dict:
    result = {
        "id": product.id,
        "business_id": product.business_id,
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "sku": product.sku,
        "barcode": product.barcode,
        "name": product.name,
        "description": product.description,
        "brand": product.brand,
        "unit": product.unit,
        "cost_price": serialize_decimal(product.cost_price),
        "selling_price": serialize_decimal(product.selling_price),
        "current_stock": serialize_decimal(product.current_stock),
        "minimum_stock": serialize_decimal(product.minimum_stock),
        "maximum_stock": serialize_decimal(product.maximum_stock),
        "is_active": product.is_active,
        "inventory_value": serialize_decimal(inventory_value_for(product)),
        "stock_status": product_stock_status(product),
        "unit_profit": serialize_decimal(unit_profit_for(product)),
        "margin_percentage": serialize_decimal(margin_percentage_for(product)),
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
    if not include_cost_details:
        for field in ("cost_price", "inventory_value", "unit_profit", "margin_percentage"):
            result.pop(field)
    return result


@router.get("", response_model=dict)
def list_products(
    search: str | None = None,
    category_id: UUID | None = None,
    low_stock: bool = False,
    out_of_stock: bool = False,
    active_only: bool = False,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Product).options(selectinload(Product.category)).where(Product.business_id == user.business_id)
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    if search:
        search_text = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(search_text),
                Product.sku.ilike(search_text),
                Product.barcode.ilike(search_text),
                Product.brand.ilike(search_text),
            )
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if low_stock:
        stmt = stmt.where(Product.current_stock <= Product.minimum_stock, Product.current_stock > 0)
    if out_of_stock:
        stmt = stmt.where(Product.current_stock == 0)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Product.name).offset((page - 1) * limit).limit(limit)
    ).all()
    return {
        "items": [
            serialize_product(item, include_cost_details=user.role != UserRole.CASHIER)
            for item in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{product_id}", response_model=dict)
def read_product(
    product_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    product = db.scalar(
        select(Product).options(selectinload(Product.category)).where(
            Product.id == product_id,
            Product.business_id == user.business_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return serialize_product(product, include_cost_details=user.role != UserRole.CASHIER)


@router.post("", response_model=dict, status_code=201)
def create_product(
    payload: ProductCreate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict:
    sku = payload.sku.strip()
    duplicate_sku = db.scalar(
        select(Product.id).where(
            Product.business_id == user.business_id,
            Product.sku == sku,
        )
    )
    if duplicate_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists in this business",
        )
    if payload.barcode:
        duplicate_barcode = db.scalar(
            select(Product.id).where(
                Product.business_id == user.business_id,
                Product.barcode == payload.barcode.strip(),
            )
        )
        if duplicate_barcode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this barcode already exists in this business",
            )
    if payload.category_id is not None:
        category = db.scalar(
            select(Category).where(
                Category.id == payload.category_id,
                Category.business_id == user.business_id,
            )
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

    product = Product(
        business_id=user.business_id,
        category_id=payload.category_id,
        sku=sku,
        barcode=(payload.barcode.strip() if payload.barcode else None),
        name=payload.name.strip(),
        description=(payload.description.strip() if payload.description else None),
        brand=(payload.brand.strip() if payload.brand else None),
        unit=payload.unit.strip() or "pcs",
        cost_price=Decimal(str(payload.cost_price)),
        selling_price=Decimal(str(payload.selling_price)),
        current_stock=Decimal(str(payload.opening_stock or 0)),
        minimum_stock=Decimal(str(payload.minimum_stock or 0)),
        maximum_stock=(Decimal(str(payload.maximum_stock)) if payload.maximum_stock is not None else None),
        is_active=payload.is_active,
    )
    db.add(product)
    db.flush()
    if payload.opening_stock is not None and payload.opening_stock > 0:
        movement = StockMovement(
            business_id=user.business_id,
            product_id=product.id,
            movement_type=MovementType.OPENING_STOCK,
            quantity=Decimal(str(payload.opening_stock)),
            previous_stock=Decimal("0"),
            new_stock=Decimal(str(payload.opening_stock)),
            unit_cost=Decimal(str(product.cost_price)),
            reference_type="product",
            reference_id=str(product.id),
            notes="Opening stock",
            created_by=user.id,
        )
        db.add(movement)
    elif payload.opening_stock is not None and payload.opening_stock == 0:
        product.current_stock = Decimal("0")
    record_audit(
        db, user.business_id, user.id, "create", "product", product.id,
        f"Created product {product.name}",
    )
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.put("/{product_id}", response_model=dict)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
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
    if payload.sku is not None:
        new_sku = payload.sku.strip()
        duplicate = db.scalar(
            select(Product.id).where(
                Product.business_id == user.business_id,
                Product.id != product_id,
                Product.sku == new_sku,
            )
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this SKU already exists in this business",
            )
        product.sku = new_sku
    if payload.barcode is not None:
        if payload.barcode.strip():
            duplicate = db.scalar(
                select(Product.id).where(
                    Product.business_id == user.business_id,
                    Product.id != product_id,
                    Product.barcode == payload.barcode.strip(),
                )
            )
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A product with this barcode already exists in this business",
                )
            product.barcode = payload.barcode.strip()
        else:
            product.barcode = None
    if "category_id" in payload.model_fields_set:
        if payload.category_id is not None:
            category = db.scalar(
                select(Category).where(
                    Category.id == payload.category_id,
                    Category.business_id == user.business_id,
                )
            )
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
                )
        product.category_id = payload.category_id
    update_fields = {
        "category_id": payload.category_id,
        "name": payload.name,
        "description": payload.description,
        "brand": payload.brand,
        "unit": payload.unit,
        "cost_price": payload.cost_price,
        "selling_price": payload.selling_price,
        "minimum_stock": payload.minimum_stock,
        "maximum_stock": payload.maximum_stock,
        "is_active": payload.is_active,
    }
    for field, value in update_fields.items():
        if value is not None:
            if field in {"name", "description", "brand", "unit"} and isinstance(value, str):
                value = value.strip() if value.strip() else None
            setattr(product, field, value)
    record_audit(
        db, user.business_id, user.id, "update", "product", product.id,
        f"Updated product {product.name}",
    )
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.delete("/{product_id}", response_model=dict)
def delete_product(
    product_id: UUID,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
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
    product.is_active = False
    record_audit(
        db, user.business_id, user.id, "deactivate", "product", product.id,
        f"Deactivated product {product.name}",
    )
    db.commit()
    db.refresh(product)
    return serialize_product(product)
