from uuid import UUID

import jwt
from enum import StrEnum
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.user import User, UserRole
from app.services.audit import record_audit

bearer_scheme = HTTPBearer(auto_error=False)


class Permission(StrEnum):
    DASHBOARD = "dashboard"
    POS = "pos"
    SALES_READ = "sales_read"
    SALES_CREATE = "sales_create"
    SALE_PAYMENT_RECEIVE = "sale_payment_receive"
    SALES_RETURN = "sales_return"
    CUSTOMER_READ = "customer_read"
    CUSTOMER_WRITE = "customer_write"
    PRODUCT_READ = "product_read"
    INVENTORY_MANAGE = "inventory_manage"
    PURCHASE_MANAGE = "purchase_manage"
    FINANCIAL_READ = "financial_read"
    FINANCIAL_WRITE = "financial_write"
    BUSINESS_READ = "business_read"
    BUSINESS_MANAGE = "business_manage"
    STAFF_MANAGE = "staff_manage"
    AUDIT_READ = "audit_read"


# Explicit allow list; permissions not listed here are denied by default.
OWNER_PERMISSIONS = frozenset(Permission)
ADMIN_PERMISSIONS = OWNER_PERMISSIONS - {Permission.STAFF_MANAGE, Permission.AUDIT_READ}
INVENTORY_PERMISSIONS = frozenset({
    Permission.DASHBOARD, Permission.PRODUCT_READ, Permission.INVENTORY_MANAGE,
    Permission.PURCHASE_MANAGE, Permission.BUSINESS_READ,
})
CASHIER_PERMISSIONS = frozenset({
    Permission.DASHBOARD, Permission.POS, Permission.SALES_READ, Permission.SALES_CREATE,
    Permission.SALE_PAYMENT_RECEIVE, Permission.CUSTOMER_READ, Permission.CUSTOMER_WRITE, Permission.PRODUCT_READ,
    Permission.BUSINESS_READ,
})
ROLE_PERMISSIONS = {
    UserRole.OWNER: OWNER_PERMISSIONS,
    UserRole.ADMIN: ADMIN_PERMISSIONS,
    UserRole.MANAGER: INVENTORY_PERMISSIONS,
    UserRole.INVENTORY_MANAGER: INVENTORY_PERMISSIONS,
    UserRole.CASHIER: CASHIER_PERMISSIONS,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required or token is invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("purpose") is not None:
            raise InvalidTokenError("Wrong token purpose")
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if (user is None or not user.is_active or not user.is_activated
            or user.must_change_password
            or payload.get("ver", 0) != user.token_version):
        raise unauthorized
    return user


def require_roles(*roles: UserRole):
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return role_dependency


def require_permission(permission: Permission):
    def permission_dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if permission not in ROLE_PERMISSIONS.get(user.role, frozenset()):
            record_audit(db, user.business_id, user.id, "permission_denied", "permission",
                         permission.value, "Denied a privileged API action")
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not have permission to perform this action")
        return user
    return permission_dependency
