from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import Permission, get_current_user, require_permission
from app.models.payment import Payment
from app.models.customer import Customer
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.models.user import User as Account
from app.schemas.commerce import CustomerPaymentCreate, SalePaymentCreate, SupplierPaymentCreate
from app.schemas.commerce import PaymentRead
from app.services.commerce import create_customer_payment, create_sale_payment, create_supplier_payment
from app.services.audit import record_audit
from app.services.dates import business_datetime_bounds

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("")
def list_payments(
    customer_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Payment).where(Payment.business_id == user.business_id)
    if customer_id:
        stmt = stmt.where(Payment.customer_id == customer_id)
    if start_date:
        start_at, _ = business_datetime_bounds(db, user.business_id, start_date, start_date)
        stmt = stmt.where(Payment.payment_date >= start_at)
    if end_date:
        _, end_at = business_datetime_bounds(db, user.business_id, end_date, end_date)
        stmt = stmt.where(Payment.payment_date < end_at)
    results = []
    for payment in db.scalars(stmt.order_by(Payment.payment_date.desc()).limit(limit)):
        supplier_name = None
        invoice_number = None
        if payment.reference_type.value == "purchase":
            try:
                purchase_id = UUID(payment.reference_id)
            except ValueError:
                purchase_id = None
            purchase = db.scalar(select(Purchase).where(
                Purchase.id == purchase_id,
                Purchase.business_id == user.business_id,
            )) if purchase_id else None
            if purchase:
                supplier_name = db.scalar(select(Supplier.name).where(
                    Supplier.id == purchase.supplier_id,
                    Supplier.business_id == user.business_id,
                ))
                invoice_number = purchase.invoice_number
        elif payment.reference_type.value in {"sale", "customer_payment", "refund"}:
            try:
                reference_id = UUID(payment.reference_id)
            except ValueError:
                reference_id = None
            if reference_id:
                sale = db.scalar(select(Sale).where(
                    Sale.id == reference_id,
                    Sale.business_id == user.business_id,
                ))
                invoice_number = sale.invoice_number if sale else None
        results.append({
            "id": payment.id,
            "business_id": payment.business_id,
            "payment_type": payment.payment_type.value,
            "reference_type": payment.reference_type.value,
            "reference_id": payment.reference_id,
            "invoice_number": invoice_number,
            "customer_id": payment.customer_id,
            "customer_name": db.scalar(select(Customer.name).where(
                Customer.id == payment.customer_id,
                Customer.business_id == user.business_id,
            )) if payment.customer_id else None,
            "supplier_name": supplier_name,
            "amount": payment.amount,
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date,
            "reference_number": payment.reference_number,
            "notes": payment.notes,
            "received_by": payment.received_by,
            "received_by_name": db.scalar(select(Account.name).where(
                Account.id == payment.received_by,
                Account.business_id == user.business_id,
            )) if payment.received_by else None,
            "created_at": payment.created_at,
        })
    return results


@router.post("/customer", response_model=list[PaymentRead], status_code=201)
def receive_customer_payment(payload: CustomerPaymentCreate, user: User = Depends(require_permission(Permission.FINANCIAL_WRITE)), db: Session = Depends(get_db)) -> list[Payment]:
    try:
        records = create_customer_payment(db, user, payload)
        for record in records:
            record_audit(
                db, user.business_id, user.id, "create", "customer_payment",
                record.id, f"Received customer payment of {record.amount}",
            )
        db.commit()
        for record in records:
            db.refresh(record)
        return records
    except Exception:
        db.rollback()
        raise


@router.post("/sale", status_code=201)
def receive_sale_payment(payload: SalePaymentCreate, user: User = Depends(require_permission(Permission.FINANCIAL_WRITE)), db: Session = Depends(get_db)) -> dict:
    try:
        payment = create_sale_payment(db, user, payload)
        record_audit(
            db, user.business_id, user.id, "create", "sale_payment",
            payment.id, f"Received sale payment of {payment.amount}",
        )
        db.commit()
        db.refresh(payment)
        return {
            "id": payment.id,
            "sale_id": payload.sale_id,
            "amount": payment.amount,
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date,
            "reference_number": payment.reference_number,
            "notes": payment.notes,
        }
    except Exception:
        db.rollback()
        raise


@router.post("/supplier", status_code=201)
def pay_supplier(
    payload: SupplierPaymentCreate,
    user: User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payment = create_supplier_payment(db, user, payload)
        record_audit(
            db, user.business_id, user.id, "create", "supplier_payment",
            payment.id, f"Recorded supplier payment of {payment.amount}",
        )
        db.commit()
        db.refresh(payment)
        return {
            "id": payment.id,
            "amount": payment.amount,
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date,
            "reference_type": payment.reference_type.value,
            "reference_id": payment.reference_id,
        }
    except Exception:
        db.rollback()
        raise
