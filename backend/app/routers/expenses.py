from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import require_roles
from app.models.expense import Expense, ExpenseCategory
from app.models.payment import PaymentMethod
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCreate, ExpenseUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/expenses", tags=["Expenses"])
MANAGERS = (UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
DEFAULT_CATEGORIES = (
    "Rent", "Utilities", "Salaries", "Transport", "Marketing",
    "Maintenance", "Office Supplies", "Internet", "Taxes", "Miscellaneous",
)


def ensure_default_categories(db: Session, business_id: UUID) -> None:
    existing = set(db.scalars(select(ExpenseCategory.name).where(
        ExpenseCategory.business_id == business_id,
    )).all())
    missing = [
        ExpenseCategory(business_id=business_id, name=name)
        for name in DEFAULT_CATEGORIES if name not in existing
    ]
    if missing:
        db.add_all(missing)
        db.commit()


def serialize_expense(db: Session, expense: Expense) -> dict:
    category = db.scalar(select(ExpenseCategory).where(
        ExpenseCategory.id == expense.category_id,
        ExpenseCategory.business_id == expense.business_id,
    ))
    creator_name = db.scalar(select(User.name).where(
        User.id == expense.created_by,
        User.business_id == expense.business_id,
    )) if expense.created_by else None
    return {
        "id": expense.id,
        "category_id": expense.category_id,
        "category_name": category.name if category else "Unknown",
        "description": expense.description,
        "amount": expense.amount,
        "expense_date": expense.expense_date,
        "payment_method": expense.payment_method.value,
        "reference_number": expense.reference_number,
        "notes": expense.notes,
        "created_by": expense.created_by,
        "created_by_name": creator_name,
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
    }


@router.get("/categories")
def list_expense_categories(
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> list[dict]:
    ensure_default_categories(db, user.business_id)
    rows = db.scalars(select(ExpenseCategory).where(
        ExpenseCategory.business_id == user.business_id,
        ExpenseCategory.is_active.is_(True),
    ).order_by(ExpenseCategory.name)).all()
    return [{"id": row.id, "name": row.name, "is_active": row.is_active} for row in rows]


@router.post("/categories", status_code=201)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> dict:
    name = payload.name.strip()
    exists = db.scalar(select(ExpenseCategory.id).where(
        ExpenseCategory.business_id == user.business_id,
        func.lower(ExpenseCategory.name) == name.lower(),
    ))
    if exists:
        raise HTTPException(status_code=409, detail="An expense category with this name already exists")
    category = ExpenseCategory(business_id=user.business_id, name=name)
    db.add(category)
    record_audit(db, user.business_id, user.id, "create", "expense_category", category.id, f"Created expense category {name}")
    db.commit()
    db.refresh(category)
    return {"id": category.id, "name": category.name, "is_active": category.is_active}


@router.get("")
def list_expenses(
    search: str | None = None,
    category_id: UUID | None = None,
    payment_method: PaymentMethod | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> dict:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    stmt = select(Expense).where(Expense.business_id == user.business_id)
    if start_date:
        stmt = stmt.where(Expense.expense_date >= start_date)
    if end_date:
        stmt = stmt.where(Expense.expense_date <= end_date)
    if category_id:
        stmt = stmt.where(Expense.category_id == category_id)
    if payment_method:
        stmt = stmt.where(Expense.payment_method == payment_method)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Expense.description.ilike(term), Expense.reference_number.ilike(term)))

    filtered = stmt.subquery()
    total_count = db.scalar(select(func.count()).select_from(filtered)) or 0
    total_amount = db.scalar(select(func.coalesce(func.sum(filtered.c.amount), 0))) or 0
    category_rows = db.execute(
        select(ExpenseCategory.name, func.sum(Expense.amount))
        .join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
        .where(Expense.business_id == user.business_id)
        .where(Expense.id.in_(select(filtered.c.id)))
        .group_by(ExpenseCategory.name)
        .order_by(ExpenseCategory.name)
    ).all()
    rows = db.execute(
        select(Expense, ExpenseCategory.name, User.name)
        .join(ExpenseCategory, and_(
            ExpenseCategory.id == Expense.category_id,
            ExpenseCategory.business_id == user.business_id,
        ))
        .outerjoin(User, and_(
            User.id == Expense.created_by,
            User.business_id == user.business_id,
        ))
        .where(Expense.business_id == user.business_id)
        .where(Expense.id.in_(select(filtered.c.id)))
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [{
            "id": expense.id,
            "category_id": expense.category_id,
            "category_name": category_name,
            "description": expense.description,
            "amount": expense.amount,
            "expense_date": expense.expense_date,
            "payment_method": expense.payment_method.value,
            "reference_number": expense.reference_number,
            "notes": expense.notes,
            "created_by": expense.created_by,
            "created_by_name": creator_name,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
        } for expense, category_name, creator_name in rows],
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_amount": total_amount,
        "category_breakdown": [{"category": name, "amount": amount} for name, amount in category_rows],
    }


@router.post("", status_code=201)
def create_expense(
    payload: ExpenseCreate,
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> dict:
    category = db.scalar(select(ExpenseCategory).where(
        ExpenseCategory.id == payload.category_id,
        ExpenseCategory.business_id == user.business_id,
        ExpenseCategory.is_active.is_(True),
    ))
    if category is None:
        raise HTTPException(status_code=404, detail="Expense category not found")
    expense = Expense(
        business_id=user.business_id,
        created_by=user.id,
        category_id=category.id,
        description=payload.description.strip(),
        amount=payload.amount,
        expense_date=payload.expense_date,
        payment_method=payload.payment_method,
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(expense)
    db.flush()
    record_audit(db, user.business_id, user.id, "create", "expense", expense.id, f"Recorded expense {expense.description}")
    db.commit()
    db.refresh(expense)
    return serialize_expense(db, expense)


@router.get("/{expense_id}")
def read_expense(
    expense_id: UUID,
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> dict:
    expense = db.scalar(select(Expense).where(
        Expense.id == expense_id,
        Expense.business_id == user.business_id,
    ))
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return serialize_expense(db, expense)


@router.put("/{expense_id}")
def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> dict:
    expense = db.scalar(select(Expense).where(
        Expense.id == expense_id,
        Expense.business_id == user.business_id,
    ))
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values and values["category_id"] is not None:
        category = db.scalar(select(ExpenseCategory).where(
            ExpenseCategory.id == values["category_id"],
            ExpenseCategory.business_id == user.business_id,
            ExpenseCategory.is_active.is_(True),
        ))
        if category is None:
            raise HTTPException(status_code=404, detail="Expense category not found")
    for field, value in values.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(expense, field, value)
    record_audit(db, user.business_id, user.id, "update", "expense", expense.id, f"Updated expense {expense.description}")
    db.commit()
    db.refresh(expense)
    return serialize_expense(db, expense)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: UUID,
    user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
) -> None:
    expense = db.scalar(select(Expense).where(
        Expense.id == expense_id,
        Expense.business_id == user.business_id,
    ))
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    record_audit(db, user.business_id, user.id, "delete", "expense", expense.id, f"Deleted expense {expense.description}")
    db.delete(expense)
    db.commit()
