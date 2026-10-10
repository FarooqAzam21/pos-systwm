from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.business import BusinessRead, BusinessUpdate
from app.services.audit import record_audit
from app.services.cache import cached_response
from app.core.config import settings

router = APIRouter(prefix="/business", tags=["Business"])


def get_user_business(user: User, db: Session) -> Business:
    business = db.get(Business, user.business_id)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Business not found"
        )
    return business


@router.get("", response_model=BusinessRead)
def read_business(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Business:
    return cached_response(
        "settings", user.business_id, user.role.value, {}, settings.settings_cache_ttl_seconds,
        lambda: get_user_business(user, db),
    )


@router.put("", response_model=BusinessRead)
def update_business(
    payload: BusinessUpdate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Business:
    business = get_user_business(user, db)
    for field, value in payload.model_dump().items():
        setattr(business, field, value)
    record_audit(
        db, user.business_id, user.id, "update", "business",
        business.id, "Updated business profile and invoice settings",
    )
    db.commit()
    db.refresh(business)
    return business
