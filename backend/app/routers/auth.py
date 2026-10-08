from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccountUpdate,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.services.auth import authenticate_user, register_business_owner
from app.services.audit import record_audit
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead(
            id=str(user.id),
            name=user.name,
            email=user.email,
            role=user.role,
            business_id=str(user.business_id),
            business_name=user.business.business_name,
            is_active=user.is_active,
        ),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return token_response(register_business_owner(payload, db))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(payload, db)
    record_audit(db, user.business_id, user.id, "login", "user", user.id, "User signed in")
    db.commit()
    return token_response(user)


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.put("/me", response_model=UserRead)
def update_me(
    payload: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.new_password and (
        not payload.current_password
        or not verify_password(payload.current_password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    duplicate = db.scalar(
        select(User.id).where(User.email == payload.email, User.id != user.id)
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    user.name = payload.name.strip()
    user.email = payload.email
    if payload.new_password:
        user.password_hash = hash_password(payload.new_password)
    record_audit(
        db, user.business_id, user.id, "update", "user", user.id,
        "Updated account profile or credentials",
    )
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
