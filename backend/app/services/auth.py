from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import secrets
from cryptography.fernet import Fernet, InvalidToken

from app.core.security import hash_password, verify_password
from app.models.business import Business
from app.models.user import User, UserRole
from app.models.activation_request import ActivationRequest
from app.core.config import settings
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit import record_audit

DUMMY_PASSWORD_HASH = hash_password("orvion-invalid-login-check-only")


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
    password_matches = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not user.is_active or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _fernet() -> Fernet:
    # Derive a purpose-specific encryption key from the existing server secret.
    return Fernet(__import__("base64").urlsafe_b64encode(sha256(("orvion-activation:" + settings.secret_key).encode()).digest()))


def _otp_digest(request: ActivationRequest, code: str) -> str:
    message = f"{request.business_id}:{request.user_id}:{request.id}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, "sha256").hexdigest()


def get_or_create_activation_request(db: Session, user: User) -> ActivationRequest:
    now = datetime.now(timezone.utc)
    pending = db.scalar(select(ActivationRequest).where(
        ActivationRequest.user_id == user.id,
        ActivationRequest.business_id == user.business_id,
        ActivationRequest.status.in_(("pending_approval", "otp_issued")),
    ).order_by(ActivationRequest.created_at.desc()).with_for_update())
    pending_expiry = pending.otp_expires_at if pending else None
    if pending_expiry and pending_expiry.tzinfo is None:
        pending_expiry = pending_expiry.replace(tzinfo=timezone.utc)
    if pending and pending.status == "otp_issued" and pending_expiry and pending_expiry <= now:
        pending.status = "expired"
        pending.otp_hmac = None
        pending.otp_encrypted = None
        pending = None
    if pending is None:
        recent = db.scalar(select(func.count(ActivationRequest.id)).where(
            ActivationRequest.user_id == user.id,
            ActivationRequest.business_id == user.business_id,
            ActivationRequest.created_at >= now - timedelta(hours=1),
        )) or 0
        if recent >= 3:
            raise HTTPException(status_code=429, detail="Activation request limit reached. Contact your workspace owner.")
        pending = ActivationRequest(business_id=user.business_id, user_id=user.id)
        db.add(pending)
        record_audit(db, user.business_id, user.id, "activation_requested", "user", user.id,
                     "Staff member requested first-login activation")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        pending = db.scalar(select(ActivationRequest).where(
            ActivationRequest.user_id == user.id,
            ActivationRequest.business_id == user.business_id,
            ActivationRequest.status.in_(("pending_approval", "otp_issued")),
        ).order_by(ActivationRequest.created_at.desc()))
        if pending is None:
            raise
    db.refresh(pending)
    return pending


def issue_activation_otp(db: Session, request: ActivationRequest) -> tuple[ActivationRequest, str]:
    now = datetime.now(timezone.utc)
    if request.status not in {"pending_approval", "otp_issued"}:
        raise HTTPException(status_code=409, detail="This activation request is no longer pending")
    existing_expiry = request.otp_expires_at
    if existing_expiry and existing_expiry.tzinfo is None:
        existing_expiry = existing_expiry.replace(tzinfo=timezone.utc)
    if request.status == "otp_issued" and existing_expiry and existing_expiry > now:
        # Existing live OTP can be retrieved through the owner-only reveal route.
        raise HTTPException(status_code=429, detail="An active activation code already exists")
    if request.otp_generated_at:
        generated_at = request.otp_generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        if generated_at > now - timedelta(seconds=60):
            raise HTTPException(status_code=429, detail="Wait before generating another activation code")
    code = f"{secrets.randbelow(1_000_000):06d}"
    request.status = "otp_issued"
    request.otp_hmac = _otp_digest(request, code)
    request.otp_encrypted = _fernet().encrypt(code.encode()).decode()
    request.otp_expires_at = now + timedelta(minutes=5)
    request.otp_generated_at = now
    request.attempts = 0
    db.commit()
    db.refresh(request)
    return request, code


def reveal_activation_otp(request: ActivationRequest) -> str:
    now = datetime.now(timezone.utc)
    expires = request.otp_expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if request.status != "otp_issued" or not request.otp_encrypted or not expires or expires <= now:
        raise HTTPException(status_code=410, detail="Activation code has expired or is unavailable")
    try:
        return _fernet().decrypt(request.otp_encrypted.encode(), ttl=300).decode()
    except (InvalidToken, ValueError):
        raise HTTPException(status_code=410, detail="Activation code has expired or is unavailable") from None


def verify_activation_otp(db: Session, request: ActivationRequest, code: str) -> User:
    request = db.scalar(select(ActivationRequest).where(ActivationRequest.id == request.id).with_for_update())
    now = datetime.now(timezone.utc)
    expires = request.otp_expires_at if request else None
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if (request is None or request.status != "otp_issued" or request.attempts >= 5
            or not expires or expires <= now or not request.otp_hmac):
        if request is not None:
            record_audit(db, request.business_id, None, "otp_expired_or_rejected", "user", request.user_id,
                         "An invalid, expired, or exhausted activation code was rejected")
            db.commit()
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired")
    expected = _otp_digest(request, code)
    if not hmac.compare_digest(request.otp_hmac, expected):
        request.attempts += 1
        if request.attempts >= 5:
            request.status = "locked"
            request.otp_hmac = None
            request.otp_encrypted = None
        record_audit(db, request.business_id, None, "otp_rejected", "user", request.user_id,
                     "An incorrect activation code was submitted")
        db.commit()
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired")
    user = db.scalar(select(User).where(
        User.id == request.user_id, User.business_id == request.business_id
    ).with_for_update())
    if user is None or not user.is_active or user.is_activated:
        request.status = "invalidated"
        request.otp_hmac = None
        request.otp_encrypted = None
        db.commit()
        raise HTTPException(status_code=400, detail="Activation code is invalid or expired")
    request.status = "verified"
    request.otp_hmac = None
    request.otp_encrypted = None
    user.is_activated = True
    user.must_change_password = True
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user
