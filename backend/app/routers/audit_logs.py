from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import Permission, require_permission
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.services.dates import business_datetime_bounds

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("")
def list_audit_logs(
    start_date: date | None = None,
    end_date: date | None = None,
    entity_type: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AuditLog).where(AuditLog.business_id == user.business_id)
    if start_date:
        start_at, _ = business_datetime_bounds(db, user.business_id, start_date, start_date)
        stmt = stmt.where(AuditLog.created_at >= start_at)
    if end_date:
        _, end_at = business_datetime_bounds(db, user.business_id, end_date, end_date)
        stmt = stmt.where(AuditLog.created_at < end_at)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(AuditLog.action.ilike(pattern), AuditLog.entity_type.ilike(pattern), AuditLog.description.ilike(pattern), AuditLog.entity_id.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    users = {account.id: account.name for account in db.scalars(select(User).where(User.business_id == user.business_id))}
    return {
        "items": [{
            "id": row.id,
            "user_id": row.user_id,
            "user_name": users.get(row.user_id),
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "description": row.description,
            "created_at": row.created_at,
        } for row in records],
        "total": total,
        "page": page,
        "limit": limit,
    }
