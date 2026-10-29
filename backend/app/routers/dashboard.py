from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import Permission, get_current_user, require_permission
from app.models.sale import Sale, SaleStatus
from app.models.user import User
from app.services.commerce import dashboard_overview
from app.services.cache import cached_response
from app.core.config import settings
from app.services.dates import (
    business_datetime_bounds,
    business_local_date_expression,
    business_today,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def get_dashboard_overview(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_permission(Permission.DASHBOARD)),
    db: Session = Depends(get_db),
) -> dict:
    today = business_today(db, user.business_id)
    end = end_date or today
    start = start_date or end - timedelta(days=6)
    if end < start:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 366 days")

    def load() -> dict:
        if user.role.value in {"Cashier", "Inventory Manager", "Manager"}:
            today_start, today_end = business_datetime_bounds(db, user.business_id, today, today)
            totals = db.execute(
                select(func.coalesce(func.sum(Sale.total_amount), 0), func.count(Sale.id)).where(
                    Sale.business_id == user.business_id,
                    Sale.sale_date >= today_start,
                    Sale.sale_date < today_end,
                    Sale.status != SaleStatus.VOIDED,
                )
            ).one()
            trend_start, trend_end = business_datetime_bounds(db, user.business_id, start, end)
            trend_day = business_local_date_expression(db, user.business_id, Sale.sale_date)
            trend_rows = db.execute(
                select(trend_day, func.sum(Sale.total_amount))
                .where(
                    Sale.business_id == user.business_id,
                    Sale.sale_date >= trend_start,
                    Sale.sale_date < trend_end,
                    Sale.status != SaleStatus.VOIDED,
                )
                .group_by(trend_day)
            ).all()
            return {
                "today": {"sales": totals[0] or 0, "transactions": totals[1]},
                "sales_trend": [{"date": str(day)[:10], "sales": total or 0} for day, total in trend_rows],
            }
        return dashboard_overview(db, user.business_id, start, end)

    return cached_response(
        "dashboard", user.business_id, user.role.value,
        {"start": start, "end": end}, settings.dashboard_cache_ttl_seconds, load,
    )
