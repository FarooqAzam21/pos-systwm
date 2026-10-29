from datetime import datetime, timezone
import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import get_db
from app.dependencies.auth import Permission, require_permission
from app.models.activation_request import ActivationRequest
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.user import StaffRead, TemporaryPasswordRead, UserCreate, UserUpdate
from app.services.auth import issue_activation_otp, reveal_activation_otp
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["Staff Management"])
staff_owner = require_permission(Permission.STAFF_MANAGE)
STAFF_ROLES = {UserRole.CASHIER, UserRole.INVENTORY_MANAGER, UserRole.MANAGER}


def _staff_read(account: User) -> StaffRead:
    return StaffRead(id=str(account.id), name=account.name, email=account.email,
                     role=account.role.value, is_active=account.is_active,
                     is_activated=account.is_activated,
                     must_change_password=account.must_change_password,
                     last_login_at=account.last_login_at)


@router.get("", response_model=list[UserRead])
def list_users(user: User = Depends(staff_owner), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.business_id == user.business_id).order_by(User.name)))


@router.get("/activation-requests")
def list_activation_requests(user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    requests = db.scalars(select(ActivationRequest).where(
        ActivationRequest.business_id == user.business_id,
        ActivationRequest.status.in_(("pending_approval", "otp_issued")),
    ).order_by(ActivationRequest.created_at.desc())).all()
    output = []
    now = datetime.now(timezone.utc)
    for request in requests:
        expires = request.otp_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if request.status == "otp_issued" and (expires is None or expires <= now):
            request.status = "expired"
            request.otp_hmac = request.otp_encrypted = None
            continue
        account = db.scalar(select(User).where(User.id == request.user_id, User.business_id == user.business_id))
        if account:
            output.append({"id": str(request.id), "user": _staff_read(account).model_dump(mode="json"),
                           "status": request.status, "created_at": request.created_at,
                           "otp_expires_at": request.otp_expires_at})
    db.commit()
    return output


@router.post("/activation-requests/{request_id}/otp")
def generate_activation_otp(request_id: UUID, response: Response, user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, private"
    request = db.scalar(select(ActivationRequest).where(
        ActivationRequest.id == request_id, ActivationRequest.business_id == user.business_id,
    ).with_for_update())
    if request is None:
        raise HTTPException(status_code=404, detail="Activation request not found")
    request, code = issue_activation_otp(db, request)
    account = db.get(User, request.user_id)
    record_audit(db, user.business_id, user.id, "otp_generated", "user", request.user_id,
                 "Generated a first-login activation code")
    db.commit()
    return {"request_id": str(request.id), "staff_name": account.name if account else None,
            "otp": code, "expires_at": request.otp_expires_at}


@router.get("/activation-requests/{request_id}/otp")
def read_activation_otp(request_id: UUID, response: Response, user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, private"
    request = db.scalar(select(ActivationRequest).where(
        ActivationRequest.id == request_id, ActivationRequest.business_id == user.business_id,
    ))
    if request is None:
        raise HTTPException(status_code=404, detail="Activation request not found")
    return {"request_id": str(request.id), "otp": reveal_activation_otp(request), "expires_at": request.otp_expires_at}


@router.delete("/activation-requests/{request_id}", status_code=204)
def reject_activation_request(request_id: UUID, user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    request = db.scalar(select(ActivationRequest).where(
        ActivationRequest.id == request_id, ActivationRequest.business_id == user.business_id,
    ).with_for_update())
    if request is None:
        raise HTTPException(status_code=404, detail="Activation request not found")
    request.status = "rejected"
    request.otp_hmac = request.otp_encrypted = None
    target = db.scalar(select(User).where(User.id == request.user_id, User.business_id == user.business_id).with_for_update())
    if target:
        target.is_active = False
        target.token_version += 1
    record_audit(db, user.business_id, user.id, "activation_rejected", "user", request.user_id,
                 "Rejected a first-login activation request")
    db.commit()


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: UUID, user: User = Depends(staff_owner), db: Session = Depends(get_db)) -> User:
    target = db.scalar(select(User).where(User.id == user_id, User.business_id == user.business_id))
    if target is None:
        raise HTTPException(status_code=404, detail="Staff account not found")
    return target


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, user: User = Depends(staff_owner), db: Session = Depends(get_db)) -> User:
    if payload.role not in {UserRole.CASHIER, UserRole.INVENTORY_MANAGER}:
        raise HTTPException(status_code=422, detail="New staff must be Cashier or Inventory Manager")
    account = User(name=payload.name.strip(), email=payload.email,
                   password_hash=hash_password(payload.password), role=payload.role,
                   business_id=user.business_id, is_active=True, is_activated=False,
                   must_change_password=True)
    db.add(account)
    try:
        db.flush()
        record_audit(db, user.business_id, user.id, "staff_created", "user", account.id,
                     f"Created staff account with role {account.role.value}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(account)
    return account


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, user: User = Depends(staff_owner), db: Session = Depends(get_db)) -> User:
    target = db.scalar(select(User).where(User.id == user_id, User.business_id == user.business_id).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="Staff account not found")
    if target.id == user.id or target.role == UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Owner account cannot be changed through staff management")
    values = payload.model_dump(exclude_unset=True)
    if values.get("role") is not None and values["role"] not in STAFF_ROLES:
        if values["role"] != target.role:
            raise HTTPException(status_code=422, detail="Staff role must be Cashier or Inventory Manager")
    old_role, old_active = target.role, target.is_active
    for field, value in values.items():
        if value is not None:
            if field in {"name", "email"} and isinstance(value, str):
                value = value.strip()
            setattr(target, field, value)
    if target.role != old_role or target.is_active != old_active:
        target.token_version += 1
        if not target.is_active:
            db.query(ActivationRequest).filter(
                ActivationRequest.user_id == target.id,
                ActivationRequest.business_id == user.business_id,
                ActivationRequest.status.in_(("pending_approval", "otp_issued")),
            ).update({"status": "invalidated", "otp_hmac": None, "otp_encrypted": None}, synchronize_session=False)
    action = "staff_deactivated" if old_active and not target.is_active else "staff_reactivated" if not old_active and target.is_active else "staff_updated"
    old_role_name = getattr(old_role, "value", old_role)
    new_role_name = getattr(target.role, "value", target.role)
    role_detail = f"; changed role from {old_role_name} to {new_role_name}" if old_role != target.role else ""
    record_audit(db, user.business_id, user.id, action, "user", target.id,
                 f"Updated staff account{role_detail}; active {target.is_active}")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(target)
    return target


@router.post("/{user_id}/password-reset", response_model=TemporaryPasswordRead)
def reset_staff_password(user_id: UUID, response: Response, user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, private"
    target = db.scalar(select(User).where(User.id == user_id, User.business_id == user.business_id).with_for_update())
    if target is None or target.role == UserRole.OWNER:
        raise HTTPException(status_code=404, detail="Staff account not found")
    # Guarantee the temporary credential meets the same character-class policy
    # as a staff-selected password; shuffle only after selecting each class.
    parts = [secrets.choice(string.ascii_lowercase), secrets.choice(string.ascii_uppercase),
             secrets.choice(string.digits), secrets.choice("!@#$%")]
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    parts.extend(secrets.choice(alphabet) for _ in range(16))
    temporary_chars = list(parts)
    secrets.SystemRandom().shuffle(temporary_chars)
    temporary = "".join(temporary_chars)
    target.password_hash = hash_password(temporary)
    target.must_change_password = True
    target.token_version += 1
    record_audit(db, user.business_id, user.id, "password_reset", "user", target.id,
                 "Owner issued a temporary staff password; prior sessions revoked")
    db.commit()
    return {"temporary_password": temporary}


@router.post("/{user_id}/revoke-sessions", status_code=204)
def revoke_staff_sessions(user_id: UUID, user: User = Depends(staff_owner), db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(User.id == user_id, User.business_id == user.business_id).with_for_update())
    if target is None or target.role == UserRole.OWNER:
        raise HTTPException(status_code=404, detail="Staff account not found")
    target.token_version += 1
    record_audit(db, user.business_id, user.id, "sessions_revoked", "user", target.id,
                 "Owner revoked all staff access tokens")
    db.commit()
