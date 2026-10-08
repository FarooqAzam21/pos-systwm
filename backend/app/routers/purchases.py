from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import require_roles
from app.models.purchase import Purchase, PurchaseItem
from app.models.payment import Payment, PaymentReferenceType
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User, UserRole
from app.schemas.commerce import PurchaseCreate
from app.services.commerce import create_purchase
from app.services.audit import record_audit

router = APIRouter(prefix="/purchases", tags=["Purchases"])
OPERATORS = (UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)


def purchase_read(db: Session, purchase: Purchase) -> dict:
    supplier = db.scalar(select(Supplier).where(
        Supplier.id == purchase.supplier_id,
        Supplier.business_id == purchase.business_id,
    ))
    items = db.scalars(select(PurchaseItem).where(
        PurchaseItem.purchase_id == purchase.id,
        PurchaseItem.business_id == purchase.business_id,
    )).all()
    return {
        "id": purchase.id,
        "business_id": purchase.business_id,
        "supplier_id": purchase.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "invoice_number": purchase.invoice_number,
        "purchase_date": purchase.purchase_date,
        "subtotal": purchase.subtotal,
        "discount": purchase.discount,
        "tax": purchase.tax,
        "total_amount": purchase.total_amount,
        "paid_amount": purchase.paid_amount,
        "outstanding_amount": purchase.outstanding_amount,
        "payment_status": purchase.payment_status.value,
        "notes": purchase.notes,
        "created_by": purchase.created_by,
        "created_at": purchase.created_at,
        "payments": [{
            "id": payment.id,
            "amount": payment.amount,
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date,
            "reference_number": payment.reference_number,
        } for payment in db.scalars(select(Payment).where(
            Payment.business_id == purchase.business_id,
            Payment.reference_type == PaymentReferenceType.PURCHASE,
            Payment.reference_id == str(purchase.id),
        ).order_by(Payment.payment_date))],
        "stock_movements": [{
            "product_id": movement.product_id,
            "product_name": db.scalar(select(Product.name).where(
                Product.id == movement.product_id,
                Product.business_id == purchase.business_id,
            )),
            "quantity": movement.quantity,
            "previous_stock": movement.previous_stock,
            "new_stock": movement.new_stock,
            "created_at": movement.created_at,
        } for movement in db.scalars(select(StockMovement).where(
            StockMovement.business_id == purchase.business_id,
            StockMovement.reference_type == "purchase",
            StockMovement.reference_id == str(purchase.id),
        ).order_by(StockMovement.created_at))],
        "items": [{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": db.scalar(select(Product.name).where(
                Product.id == item.product_id,
                Product.business_id == purchase.business_id,
            )),
            "quantity": item.quantity,
            "unit_cost": item.unit_cost,
            "discount": item.discount,
            "tax": item.tax,
            "total": item.total,
        } for item in items],
    }


@router.get("")
def list_purchases(
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(require_roles(*OPERATORS)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Purchase).where(Purchase.business_id == user.business_id)
    if search:
        stmt = stmt.where(Purchase.invoice_number.ilike(f"%{search.strip()}%"))
    if start_date:
        stmt = stmt.where(Purchase.purchase_date >= start_date)
    if end_date:
        stmt = stmt.where(Purchase.purchase_date <= end_date)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    purchases = db.scalars(stmt.order_by(Purchase.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    return {"items": [purchase_read(db, item) for item in purchases], "total": total, "page": page, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_purchase(
    payload: PurchaseCreate,
    user: User = Depends(require_roles(*OPERATORS)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        purchase = create_purchase(db, user, payload)
        record_audit(
            db, user.business_id, user.id, "create", "purchase", purchase.id,
            f"Created purchase {purchase.invoice_number}",
        )
        db.commit()
        db.refresh(purchase)
        return purchase_read(db, purchase)
    except Exception:
        db.rollback()
        raise


@router.get("/{purchase_id}")
def get_purchase(purchase_id: UUID, user: User = Depends(require_roles(*OPERATORS)), db: Session = Depends(get_db)) -> dict:
    purchase = db.scalar(select(Purchase).where(
        Purchase.id == purchase_id,
        Purchase.business_id == user.business_id,
    ))
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase_read(db, purchase)
