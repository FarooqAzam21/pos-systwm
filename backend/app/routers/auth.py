from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.activation_request import ActivationRequest
from app.models.user import User
from app.schemas.auth import (AccountUpdate, ActivationVerifyRequest, LoginRequest,
                              PasswordChangeRequest, RegisterRequest, TokenResponse, UserRead)
from app.services.auth import (authenticate_user, get_or_create_activation_request,
                               register_business_owner, verify_activation_otp)
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.token_version),
        user=UserRead(
            id=str(user.id), name=user.name, email=user.email, role=user.role,
            business_id=str(user.business_id), business_name=user.business.business_name,
            is_active=user.is_active, is_activated=user.is_activated,
            must_change_password=user.must_change_password, last_login_at=user.last_login_at,
        ),
    )


def _password_challenge(user: User, request_id: UUID | None = None) -> str:
    claims = {
        "sub": str(user.id), "ver": user.token_version, "purpose": "password_change",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    if request_id:
        claims["rid"] = str(request_id)
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store, private"
    user = register_business_owner(payload, db)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return token_response(user)


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, private"
    try:
        user = authenticate_user(payload, db)
    except HTTPException:
        account = db.scalar(select(User).where(User.email == payload.email))
        if account is not None:
            record_audit(db, account.business_id, None, "login_failed", "user", account.id,
                         "Invalid credentials were submitted")
            db.commit()
        raise
    if not user.is_activated:
        request = get_or_create_activation_request(db, user)
        return {"activation_required": True, "request_id": str(request.id)}
    if user.must_change_password:
        return {"password_change_required": True, "challenge_token": _password_challenge(user)}
    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, user.business_id, user.id, "login", "user", user.id, "User signed in")
    db.commit()
    db.refresh(user)
    return token_response(user)


@router.post("/activation/verify")
def verify_activation(payload: ActivationVerifyRequest, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, private"
    request = db.scalar(select(ActivationRequest).where(ActivationRequest.id == payload.request_id))
    if request is None:
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired")
    user = verify_activation_otp(db, request, payload.otp)
    record_audit(db, user.business_id, None, "activation_verified", "user", user.id, "Staff first-login code verified")
    db.commit()
    return {"password_change_required": True, "challenge_token": _password_challenge(user, request.id)}


@router.post("/activation/password", response_model=TokenResponse)
def activation_password(payload: PasswordChangeRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store, private"
    try:
        claims = jwt.decode(payload.challenge_token, settings.secret_key, algorithms=[settings.algorithm])
        if claims.get("purpose") != "password_change":
            raise jwt.InvalidTokenError("wrong purpose")
        user_id = UUID(claims["sub"])
        request_id = UUID(claims["rid"]) if claims.get("rid") else None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Password setup session expired. Sign in again.") from None
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if (user is None or not user.is_active or not user.is_activated or not user.must_change_password
            or claims.get("ver") != user.token_version):
        raise HTTPException(status_code=401, detail="Password setup session expired. Sign in again.")
    activation = None
    if request_id:
        activation = db.scalar(select(ActivationRequest).where(
            ActivationRequest.id == request_id, ActivationRequest.user_id == user.id,
            ActivationRequest.business_id == user.business_id,
        ).with_for_update())
        if activation is None or activation.status != "verified":
            raise HTTPException(status_code=401, detail="Password setup session expired. Sign in again.")
        activation.status = "completed"
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.token_version += 1
    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, user.business_id, user.id, "password_changed", "user", user.id, "Completed required password change")
    db.commit()
    db.refresh(user)
    return token_response(user)


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.put("/me", response_model=UserRead)
def update_me(payload: AccountUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if payload.new_password and (not payload.current_password or not verify_password(payload.current_password, user.password_hash)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    duplicate = db.scalar(select(User.id).where(User.email == payload.email, User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    user.name = payload.name.strip()
    user.email = payload.email
    if payload.new_password:
        user.password_hash = hash_password(payload.new_password)
        user.token_version += 1
    record_audit(db, user.business_id, user.id, "update", "user", user.id, "Updated account profile or credentials")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists") from None
    db.refresh(user)
    return user
