from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User


def decimal_value(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid numeric value provided",
        ) from None


def normalized_decimal(value) -> str:
    decimal_value_ = decimal_value(value)
    normalized = decimal_value_.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    formatted = format(normalized, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def normalized_decimal_value(value) -> Decimal:
    return Decimal(normalized_decimal(value))


def stock_status_for(current_stock: Decimal, minimum_stock: Decimal) -> str:
    current = decimal_value(current_stock)
    minimum = decimal_value(minimum_stock)
    if current == 0:
        return "OUT_OF_STOCK"
    if current <= minimum and current > 0:
        return "LOW_STOCK"
    return "IN_STOCK"


def inventory_value_for(product: Product) -> Decimal:
    return decimal_value(product.current_stock) * decimal_value(product.cost_price)


def unit_profit_for(product: Product) -> Decimal:
    return decimal_value(product.selling_price) - decimal_value(product.cost_price)


def margin_percentage_for(product: Product) -> Decimal:
    selling_price = decimal_value(product.selling_price)
    if selling_price == 0:
        return Decimal("0")
    return (unit_profit_for(product) / selling_price) * Decimal("100")


def set_product_status(product: Product, *, active: bool) -> None:
    product.is_active = active


def with_business_filter(query, business_id):
    return query.where(business_id is not None)


def ensure_stock_is_valid(product: Product, new_stock: Decimal, *, movement_type: str) -> None:
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{movement_type.replace('_', ' ').title()} would make inventory negative",
        )


def apply_stock_change(
    db: Session,
    product: Product,
    *,
    movement_type: str,
    quantity: Decimal,
    created_by: User,
    unit_cost: Decimal | None = None,
    notes: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> StockMovement:
    quantity_value = decimal_value(quantity)
    if quantity_value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero",
        )

    current_stock = decimal_value(product.current_stock)
    previous_stock = current_stock
    adjustment_map = {
        MovementType.OPENING_STOCK.value: Decimal("1"),
        MovementType.PURCHASE.value: Decimal("1"),
        MovementType.RETURN.value: Decimal("1"),
        MovementType.ADJUSTMENT_IN.value: Decimal("1"),
        MovementType.TRANSFER_IN.value: Decimal("1"),
        MovementType.SALE.value: Decimal("-1"),
        MovementType.ADJUSTMENT_OUT.value: Decimal("-1"),
        MovementType.DAMAGE.value: Decimal("-1"),
        MovementType.TRANSFER_OUT.value: Decimal("-1"),
    }
    if movement_type not in adjustment_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported stock movement type",
        )

    multiplier = adjustment_map[movement_type]
    new_stock = current_stock + (quantity_value * multiplier)
    ensure_stock_is_valid(product, new_stock, movement_type=movement_type)

    product.current_stock = new_stock
    movement = StockMovement(
        business_id=product.business_id,
        product_id=product.id,
        movement_type=MovementType(movement_type),
        quantity=quantity_value,
        previous_stock=previous_stock,
        new_stock=new_stock,
        unit_cost=unit_cost,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_by=created_by.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(product)
    db.refresh(movement)
    return movement


def product_query_for_business(db: Session, business_id, *, include_inactive: bool = True):
    stmt = select(Product).where(Product.business_id == business_id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    return db.scalars(stmt.order_by(Product.name)).all()


def low_stock_products(db: Session, business_id):
    products = product_query_for_business(db, business_id, include_inactive=True)
    return [product for product in products if product.current_stock <= product.minimum_stock and product.current_stock > 0]


def out_of_stock_products(db: Session, business_id):
    products = product_query_for_business(db, business_id, include_inactive=True)
    return [product for product in products if product.current_stock == 0]


def product_category_name(product: Product) -> str | None:
    return product.category.name if product.category else None


def product_stock_status(product: Product) -> str:
    return stock_status_for(product.current_stock, product.minimum_stock)


def category_total_products(db: Session, business_id, category_id):
    return db.scalar(
        select(Product.id).where(Product.business_id == business_id, Product.category_id == category_id).count()
    )


def validate_category_ownership(db: Session, business_id, category_id: str):
    category = db.get(Category, category_id)
    if category is None or category.business_id != business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category
