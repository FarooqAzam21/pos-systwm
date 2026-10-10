from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import require_roles
from app.models.supplier import Supplier
from app.models.purchase import Purchase
from app.models.user import User, UserRole
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


def supplier_read(db: Session, supplier: Supplier, outstanding=None) -> dict:
    if outstanding is None:
        outstanding = db.scalar(
            select(func.coalesce(func.sum(Purchase.outstanding_amount), 0)).where(
                Purchase.business_id == supplier.business_id,
                Purchase.supplier_id == supplier.id,
            )
        ) or 0
    return {
        "id": supplier.id,
        "business_id": supplier.business_id,
        "name": supplier.name,
        "company_name": supplier.company_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "tax_number": supplier.tax_number,
        "notes": supplier.notes,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at,
        "updated_at": supplier.updated_at,
        "outstanding_balance": outstanding,
    }


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict]:
    suppliers = db.scalars(
        select(Supplier)
        .where(Supplier.business_id == user.business_id)
        .order_by(Supplier.name)
    ).all()
    if not suppliers:
        return []
    balances = dict(db.execute(
        select(Purchase.supplier_id, func.coalesce(func.sum(Purchase.outstanding_amount), 0))
        .where(
            Purchase.business_id == user.business_id,
            Purchase.supplier_id.in_([supplier.id for supplier in suppliers]),
        )
        .group_by(Purchase.supplier_id)
    ).all())
    return [supplier_read(db, supplier, balances.get(supplier.id, 0)) for supplier in suppliers]


@router.get("/{supplier_id}", response_model=SupplierRead)
def read_supplier(
    supplier_id: UUID,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == user.business_id,
        )
    )
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    return supplier_read(db, supplier)


@router.post("", response_model=SupplierRead, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = Supplier(
        business_id=user.business_id,
        name=payload.name.strip(),
        company_name=(payload.company_name.strip() if payload.company_name else None),
        email=(payload.email.strip() if payload.email else None),
        phone=payload.phone.strip() if payload.phone else None,
        address=payload.address.strip() if payload.address else None,
        tax_number=(payload.tax_number.strip() if payload.tax_number else None),
        notes=(payload.notes.strip() if payload.notes else None),
        is_active=payload.is_active,
    )
    db.add(supplier)
    db.flush()
    record_audit(db, user.business_id, user.id, "create", "supplier", supplier.id, f"Created supplier {supplier.name}")
    db.commit()
    db.refresh(supplier)
    return supplier_read(db, supplier)


@router.put("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == user.business_id,
        )
    )
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "email" and value is not None:
            value = value.strip()
        if field in {"name", "company_name", "phone", "address", "tax_number", "notes"} and value is not None:
            value = value.strip() if isinstance(value, str) else value
        if field == "is_active" and value is None:
            continue
        setattr(supplier, field, value)
    record_audit(db, user.business_id, user.id, "update", "supplier", supplier.id, f"Updated supplier {supplier.name}")
    db.commit()
    db.refresh(supplier)
    return supplier_read(db, supplier)


@router.delete("/{supplier_id}", response_model=SupplierRead)
def delete_supplier(
    supplier_id: UUID,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == user.business_id,
        )
    )
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    supplier.is_active = False
    record_audit(db, user.business_id, user.id, "deactivate", "supplier", supplier.id, f"Deactivated supplier {supplier.name}")
    db.commit()
    db.refresh(supplier)
    return supplier
