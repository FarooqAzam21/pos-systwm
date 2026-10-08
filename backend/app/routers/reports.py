from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import require_roles
from app.models.business import Business
from app.models.daily_closing import DailyClosing
from app.models.user import User, UserRole
from app.services.reports import (
    REPORT_FIELDS,
    daily_closing,
    dashboard_analytics,
    financial_summary,
    get_report_data,
    make_excel_report,
    make_pdf_report,
    normalize_range,
)
from app.services.dates import business_today
from app.services.audit import record_audit

router = APIRouter(prefix="/reports", tags=["Reports"])
REPORT_ROLES = (UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
P_AND_L_FIELDS = ["metric", "amount"]
DAILY_CLOSING_FIELDS = [
    "total_sales",
    "opening_cash",
    "cash_sales",
    "customer_payments",
    "supplier_payments",
    "refunds",
    "expected_closing_cash",
    "actual_closing_cash",
    "variance",
    "total_returns",
    "net_sales",
    "cash_received",
    "card_received",
    "bank_transfer",
    "mobile_wallet",
    "other_payments",
    "purchases",
    "expenses",
    "cogs",
    "gross_profit",
    "net_profit",
    "closed_by",
    "closed_at",
    "notes",
]
PDF_REPORTS = {"sales", "purchases", "expenses", "inventory", "product-profitability", "profit-and-loss", "daily-closing"}


class DailyClosingCreate(BaseModel):
    report_date: date
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    actual_closing_cash: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
FINANCIAL_FILTERS = {
    "customer_id": UUID | None,
    "cashier_id": UUID | None,
    "supplier_id": UUID | None,
    "category_id": UUID | None,
    "product_id": UUID | None,
    "payment_method": str | None,
    "payment_type": str | None,
    "payment_status": str | None,
    "status": str | None,
    "movement_type": str | None,
    "search": str | None,
}


def _report_data(
    db: Session,
    business_id,
    report_name: str,
    start: date,
    end: date,
    filters: dict,
    page: int,
    limit: int,
) -> tuple[dict, list[str]]:
    if report_name == "profit-and-loss":
        summary = financial_summary(db, business_id, start, end)
        rows = [
            {"metric": name.replace("_", " ").title(), "amount": summary[key]}
            for key, name in (
                ("revenue", "Gross Revenue"),
                ("discounts", "Discounts"),
                ("returns", "Returns / Refunds"),
                ("net_revenue", "Net Revenue"),
                ("cogs", "COGS"),
                ("gross_profit", "Gross Profit"),
                ("operating_expenses", "Operating Expenses"),
                ("net_profit", "Net Profit"),
            )
        ]
        return {"items": rows, "total": len(rows), "summary": summary, **summary}, P_AND_L_FIELDS
    if report_name == "daily-closing":
        summary = daily_closing(db, business_id, start)
        return {
            "items": [{field: summary[field] for field in DAILY_CLOSING_FIELDS}],
            "total": 1,
            "summary": summary,
        }, DAILY_CLOSING_FIELDS
    if report_name not in REPORT_FIELDS:
        raise HTTPException(status_code=404, detail="Report not found")
    return get_report_data(db, business_id, report_name, start, end, filters, page, limit), REPORT_FIELDS[report_name]


def _range(db: Session, business_id, start_date: date | None, end_date: date | None) -> tuple[date, date]:
    try:
        return normalize_range(start_date, end_date or business_today(db, business_id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/dashboard")
def read_dashboard_analytics(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    start, end = _range(db, user.business_id, start_date, end_date)
    return dashboard_analytics(db, user.business_id, start, end)


@router.get("/profit-and-loss")
def read_profit_and_loss(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    start, end = _range(db, user.business_id, start_date, end_date)
    data, _ = _report_data(db, user.business_id, "profit-and-loss", start, end, {}, 1, 50)
    return data


@router.get("/daily-closing")
def read_daily_closing(
    report_date: date | None = None,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    report_day = report_date or business_today(db, user.business_id)
    summary = daily_closing(db, user.business_id, report_day)
    return {
        "items": [{field: summary[field] for field in DAILY_CLOSING_FIELDS}],
        "total": 1,
        "summary": summary,
    }


@router.post("/daily-closing", status_code=201)
def create_daily_closing(
    payload: DailyClosingCreate,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.scalar(select(DailyClosing).where(
        DailyClosing.business_id == user.business_id,
        DailyClosing.closing_date == payload.report_date,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="This business date is already closed")
    closing = DailyClosing(
        business_id=user.business_id,
        closing_date=payload.report_date,
        opening_cash=payload.opening_cash,
        actual_closing_cash=payload.actual_closing_cash,
        notes=payload.notes,
        closed_by=user.id,
    )
    db.add(closing)
    db.flush()
    record_audit(db, user.business_id, user.id, "create", "daily_closing", closing.id, f"Closed business date {payload.report_date.isoformat()}")
    db.commit()
    summary = daily_closing(db, user.business_id, payload.report_date)
    return {"items": [{field: summary[field] for field in DAILY_CLOSING_FIELDS}], "total": 1, "summary": summary}


@router.get("/{report_name}/export.xlsx")
def export_excel(
    report_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
    customer_id: UUID | None = None,
    cashier_id: UUID | None = None,
    supplier_id: UUID | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
    payment_method: str | None = None,
    payment_type: str | None = None,
    payment_status: str | None = None,
    status: str | None = None,
    movement_type: str | None = None,
    search: str | None = None,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    start, end = _range(db, user.business_id, start_date, end_date)
    filters = {
        "customer_id": customer_id,
        "cashier_id": cashier_id,
        "supplier_id": supplier_id,
        "category_id": category_id,
        "product_id": product_id,
        "payment_method": payment_method,
        "payment_type": payment_type,
        "payment_status": payment_status,
        "status": status,
        "movement_type": movement_type,
        "search": search,
    }
    data, fields = _report_data(db, user.business_id, report_name, start, end, filters, 1, 10000)
    business = db.get(Business, user.business_id)
    content = make_excel_report(
        business.business_name if business else "Business",
        report_name.replace("-", " ").title(),
        start,
        end,
        fields,
        data["items"],
        data["summary"],
    )
    filename = f"{report_name}-{start.isoformat()}-to-{end.isoformat()}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_name}/export.pdf")
def export_pdf(
    report_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
    customer_id: UUID | None = None,
    cashier_id: UUID | None = None,
    supplier_id: UUID | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
    payment_method: str | None = None,
    payment_type: str | None = None,
    payment_status: str | None = None,
    status: str | None = None,
    movement_type: str | None = None,
    search: str | None = None,
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    if report_name not in PDF_REPORTS:
        raise HTTPException(status_code=404, detail="PDF export is not available for this report")
    start, end = _range(db, user.business_id, start_date, end_date)
    filters = {
        "customer_id": customer_id,
        "cashier_id": cashier_id,
        "supplier_id": supplier_id,
        "category_id": category_id,
        "product_id": product_id,
        "payment_method": payment_method,
        "payment_type": payment_type,
        "payment_status": payment_status,
        "status": status,
        "movement_type": movement_type,
        "search": search,
    }
    data, fields = _report_data(db, user.business_id, report_name, start, end, filters, 1, 10000)
    business = db.get(Business, user.business_id)
    content = make_pdf_report(
        business.business_name if business else "Business",
        report_name.replace("-", " ").title(),
        start,
        end,
        fields,
        data["items"],
        data["summary"],
    )
    filename = f"{report_name}-{start.isoformat()}-to-{end.isoformat()}.pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_name}")
def read_report(
    report_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
    customer_id: UUID | None = None,
    cashier_id: UUID | None = None,
    supplier_id: UUID | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
    payment_method: str | None = None,
    payment_type: str | None = None,
    payment_status: str | None = None,
    status: str | None = None,
    movement_type: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    start, end = _range(db, user.business_id, start_date, end_date)
    filters = {
        "customer_id": customer_id,
        "cashier_id": cashier_id,
        "supplier_id": supplier_id,
        "category_id": category_id,
        "product_id": product_id,
        "payment_method": payment_method,
        "payment_type": payment_type,
        "payment_status": payment_status,
        "status": status,
        "movement_type": movement_type,
        "search": search,
    }
    data, _ = _report_data(db, user.business_id, report_name, start, end, filters, page, limit)
    return data
