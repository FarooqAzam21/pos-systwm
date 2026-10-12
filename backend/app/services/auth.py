from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest


def register_business_owner(payload: RegisterRequest, db: Session) -> User:
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match",
        )
    existing = db.scalar(select(User.id).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    business = Business(
        business_name=payload.business_name.strip(),
        logo=payload.logo.strip() if payload.logo else None,
        owner_name=payload.owner_name.strip(),
        email=payload.email,
    )
    user = User(
        name=payload.owner_name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.OWNER,
        business=business,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)
    return user


def authenticate_user(payload: LoginRequest, db: Session) -> User:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
