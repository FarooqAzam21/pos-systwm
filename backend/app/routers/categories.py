from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.category import Category
from app.models.user import User, UserRole
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.audit import record_audit
from app.services.cache import cached_response
from app.core.config import settings

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Category]:
    return cached_response(
        "categories", user.business_id, user.role.value, {}, settings.catalog_cache_ttl_seconds,
        lambda: list(db.scalars(
            select(Category).where(Category.business_id == user.business_id).order_by(Category.name)
        )),
    )


@router.get("/{category_id}", response_model=CategoryRead)
def read_category(
    category_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.business_id == user.business_id,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Category:
    name = payload.name.strip()
    duplicate = db.scalar(
        select(Category.id).where(
            Category.business_id == user.business_id,
            Category.name == name,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists in this business",
        )
    category = Category(
        business_id=user.business_id,
        name=name,
        description=(payload.description.strip() if payload.description else None),
        is_active=payload.is_active,
    )
    db.add(category)
    db.flush()
    record_audit(db, user.business_id, user.id, "create", "category", category.id, f"Created category {category.name}")
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.business_id == user.business_id,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    if payload.name is not None:
        name = payload.name.strip()
        if name:
            duplicate = db.scalar(
                select(Category.id).where(
                    Category.business_id == user.business_id,
                    Category.id != category_id,
                    Category.name == name,
                )
            )
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A category with this name already exists in this business",
                )
            category.name = name
    if payload.description is not None:
        category.description = payload.description.strip() or None
    if payload.is_active is not None:
        category.is_active = payload.is_active
    record_audit(db, user.business_id, user.id, "update", "category", category.id, f"Updated category {category.name}")
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=CategoryRead)
def delete_category(
    category_id: UUID,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.business_id == user.business_id,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    category.is_active = False
    record_audit(db, user.business_id, user.id, "deactivate", "category", category.id, f"Deactivated category {category.name}")
    db.commit()
    db.refresh(category)
    return category
