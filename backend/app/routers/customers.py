from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import Permission, get_current_user, require_permission
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.schemas.commerce import CustomerCreate, CustomerListRead, CustomerRead, CustomerUpdate
from app.services.commerce import (
    create_customer,
    customer_detail,
    remove_sale_cost_details,
    update_customer,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("")
def list_customers(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(require_permission(Permission.CUSTOMER_READ)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Customer).where(Customer.business_id == user.business_id)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(term), Customer.phone.ilike(term), Customer.email.ilike(term)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Customer.name).offset((page - 1) * limit).limit(limit)).all()
    if user.role == UserRole.CASHIER:
        # POS lookup needs customer identity only; never expose credit/balance data.
        return {"items": [{"id": item.id, "name": item.name, "phone": item.phone,
                           "email": item.email, "is_active": item.is_active}
                          for item in items], "total": total, "page": page, "limit": limit}
    return CustomerListRead(items=items, total=total, page=page, limit=limit).model_dump()


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def add_customer(payload: CustomerCreate, user: User = Depends(require_permission(Permission.CUSTOMER_WRITE)), db: Session = Depends(get_db)) -> Customer:
    customer = create_customer(db, user.business_id, payload)
    record_audit(db, user.business_id, user.id, "create", "customer", customer.id, f"Created customer {customer.name}")
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}")
def get_customer(customer_id: UUID, user: User = Depends(require_permission(Permission.FINANCIAL_READ)), db: Session = Depends(get_db)) -> dict:
    result = customer_detail(db, user.business_id, customer_id)
    return result


@router.put("/{customer_id}", response_model=CustomerRead)
def edit_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == user.business_id))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if "current_balance" in payload.model_fields_set:
        raise HTTPException(status_code=422, detail="Customer balance is changed only by financial transactions")
    update_customer(db, customer, payload)
    record_audit(db, user.business_id, user.id, "update", "customer", customer.id, f"Updated customer {customer.name}")
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", response_model=CustomerRead)
def deactivate_customer(customer_id: UUID, user: User = Depends(require_permission(Permission.INVENTORY_MANAGE)), db: Session = Depends(get_db)) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == user.business_id))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_active = False
    record_audit(db, user.business_id, user.id, "deactivate", "customer", customer.id, f"Deactivated customer {customer.name}")
    db.commit()
    db.refresh(customer)
    return customer
