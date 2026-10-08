from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import hash_password
from app.dependencies.auth import require_roles
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["Users"])
USER_ADMINS = (UserRole.OWNER, UserRole.ADMIN)
USER_READERS = (*USER_ADMINS, UserRole.MANAGER)


@router.get("", response_model=list[UserRead])
def list_users(
    user: User = Depends(require_roles(*USER_READERS)),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.business_id == user.business_id).order_by(User.name)
        )
    )


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: UUID,
    user: User = Depends(require_roles(*USER_READERS)),
    db: Session = Depends(get_db),
) -> User:
    target = db.scalar(
        select(User).where(
            User.id == user_id,
            User.business_id == user.business_id,
        )
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return target


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    user: User = Depends(require_roles(*USER_ADMINS)),
    db: Session = Depends(get_db),
) -> User:
    if payload.role == UserRole.OWNER and user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only an owner can assign the owner role")
    account = User(
        name=payload.name.strip(),
        email=str(payload.email).strip().lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        business_id=user.business_id,
        is_active=True,
    )
    db.add(account)
    try:
        db.flush()
        record_audit(
            db, user.business_id, user.id, "create", "user", account.id,
            f"Created user account {account.email} with role {account.role.value}",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(account)
    return account


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    user: User = Depends(require_roles(*USER_ADMINS)),
    db: Session = Depends(get_db),
) -> User:
    target = db.scalar(select(User).where(
        User.id == user_id,
        User.business_id == user.business_id,
    ))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.ADMIN and (
        target.role == UserRole.OWNER or payload.role == UserRole.OWNER
    ):
        raise HTTPException(status_code=403, detail="Admins cannot manage owner accounts")
    if target.id == user.id and payload.role is not None and payload.role != user.role:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    if target.id == user.id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    values = payload.model_dump(exclude_unset=True)
    previous_role = target.role
    for field, value in values.items():
        if value is not None:
            setattr(target, field, value.strip().lower() if field == "email" else value.strip() if field == "name" else value)
    try:
        db.flush()
        details = [f"Updated user account {target.email}"]
        if target.role != previous_role:
            details.append(f"changed role from {previous_role.value} to {target.role.value}")
        record_audit(
            db, user.business_id, user.id, "update", "user", target.id,
            "; ".join(details),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(target)
    return target
