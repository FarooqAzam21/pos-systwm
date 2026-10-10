from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import require_roles
from app.models.product import Product
from app.models.purchase import Purchase
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.schemas.commerce import PurchaseCreate
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderStatusUpdate
from app.services.audit import record_audit
from app.services.commerce import create_purchase

router = APIRouter(prefix="/purchase-orders", tags=["Purchase orders"])
OPERATORS = (UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)


def read_order(db: Session, order: PurchaseOrder) -> dict:
    supplier = db.scalar(select(Supplier).where(Supplier.id == order.supplier_id, Supplier.business_id == order.business_id))
    items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == order.id)).all()
    return {
        "id": order.id, "business_id": order.business_id, "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else "", "purchase_id": order.purchase_id,
        "order_number": order.order_number, "status": order.status,
        "expected_delivery_date": order.expected_delivery_date, "notes": order.notes,
        "created_at": order.created_at,
        "items": [{"id": item.id, "product_id": item.product_id,
                   "product_name": db.scalar(select(Product.name).where(Product.id == item.product_id, Product.business_id == order.business_id)),
                   "sku": db.scalar(select(Product.sku).where(Product.id == item.product_id, Product.business_id == order.business_id)),
                   "quantity": item.quantity, "expected_unit_cost": item.expected_unit_cost} for item in items],
    }


@router.get("")
def list_orders(search: str | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=200), user: User = Depends(require_roles(*OPERATORS)), db: Session = Depends(get_db)):
    stmt = select(PurchaseOrder).where(PurchaseOrder.business_id == user.business_id)
    if search:
        stmt = stmt.where(PurchaseOrder.order_number.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    return {"items": [read_order(db, row) for row in rows], "total": total, "page": page, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(payload: PurchaseOrderCreate, user: User = Depends(require_roles(*OPERATORS)), db: Session = Depends(get_db)):
    supplier = db.scalar(select(Supplier).where(Supplier.id == payload.supplier_id, Supplier.business_id == user.business_id, Supplier.is_active.is_(True)))
    if not supplier:
        raise HTTPException(status_code=404, detail="Active supplier not found")
    product_ids = {line.product_id for line in payload.items}
    if len(product_ids) != len(payload.items):
        raise HTTPException(status_code=422, detail="Each product can appear only once on a supplier order")
    products = db.scalars(select(Product).where(Product.business_id == user.business_id, Product.id.in_(product_ids), Product.is_active.is_(True))).all()
    if len(products) != len(product_ids):
        raise HTTPException(status_code=404, detail="One or more active products were not found")
    order = PurchaseOrder(business_id=user.business_id, supplier_id=supplier.id, order_number="", created_by=user.id, expected_delivery_date=payload.expected_delivery_date, notes=payload.notes)
    db.add(order)
    db.flush()
    order.order_number = f"PO-{str(order.id)[:8].upper()}"
    for line in payload.items:
        db.add(PurchaseOrderItem(business_id=user.business_id, purchase_order_id=order.id, product_id=line.product_id, quantity=line.quantity, expected_unit_cost=line.expected_unit_cost))
    record_audit(db, user.business_id, user.id, "create", "purchase_order", order.id, f"Created supplier order {order.order_number}")
    db.commit()
    db.refresh(order)
    return read_order(db, order)


@router.patch("/{order_id}")
def update_order_status(order_id: UUID, payload: PurchaseOrderStatusUpdate, user: User = Depends(require_roles(*OPERATORS)), db: Session = Depends(get_db)):
    order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.business_id == user.business_id))
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if order.status != "draft" or payload.status not in ("ordered", "cancelled"):
        raise HTTPException(status_code=409, detail="Only draft orders can be marked ordered or cancelled")
    order.status = payload.status
    record_audit(db, user.business_id, user.id, "update", "purchase_order", order.id, f"Marked {order.order_number} {payload.status}")
    db.commit()
    db.refresh(order)
    return read_order(db, order)


@router.post("/{order_id}/receive", status_code=status.HTTP_201_CREATED)
def receive_order(order_id: UUID, payload: PurchaseCreate, user: User = Depends(require_roles(*OPERATORS)), db: Session = Depends(get_db)):
    order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.business_id == user.business_id))
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if order.status != "ordered":
        raise HTTPException(status_code=409, detail="Only ordered supplier orders can be received")
    if payload.supplier_id != order.supplier_id:
        raise HTTPException(status_code=422, detail="Purchase supplier must match the supplier order")
    ordered = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == order.id)).all()
    expected = {line.product_id: line.quantity for line in ordered}
    received = {line.product_id: line.quantity for line in payload.items}
    if expected != received or len(received) != len(payload.items):
        raise HTTPException(status_code=422, detail="Received products and quantities must match the supplier order")
    try:
        purchase = create_purchase(db, user, payload)
        order.purchase_id = purchase.id
        order.status = "received"
        record_audit(db, user.business_id, user.id, "receive", "purchase_order", order.id, f"Received {order.order_number} as purchase {purchase.invoice_number}")
        db.commit()
        db.refresh(order)
        return {**read_order(db, order), "purchase": {"id": purchase.id, "invoice_number": purchase.invoice_number}}
    except Exception:
        db.rollback()
        raise
