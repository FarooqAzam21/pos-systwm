from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business import Business


def get_business_timezone(db: Session, business_id) -> ZoneInfo:
    timezone_name = db.scalar(
        select(Business.timezone).where(Business.id == business_id)
    ) or "UTC"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Invalid business timezone: {timezone_name}") from error


def business_today(db: Session, business_id) -> date:
    return datetime.now(timezone.utc).astimezone(
        get_business_timezone(db, business_id)
    ).date()


def business_datetime_bounds(
    db: Session,
    business_id,
    start: date,
    end: date,
) -> tuple[datetime, datetime]:
    business_timezone = get_business_timezone(db, business_id)
    start_at = datetime.combine(start, time.min, tzinfo=business_timezone)
    end_at = datetime.combine(end + timedelta(days=1), time.min, tzinfo=business_timezone)
    return start_at.astimezone(timezone.utc), end_at.astimezone(timezone.utc)


def business_local_date_expression(db: Session, business_id, value):
    business_timezone = get_business_timezone(db, business_id)
    if db.get_bind().dialect.name == "postgresql":
        return func.date(func.timezone(business_timezone.key, value))
    return func.date(value)
