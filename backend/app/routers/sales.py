from datetime import date
from decimal import Decimal
from io import BytesIO
import ipaddress
import socket
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.customer import Customer
from app.database.session import get_db
from app.dependencies.auth import Permission, get_current_user, require_permission
from app.models.payment import Payment, PaymentReferenceType
from app.models.sale import Sale, SalePaymentStatus
from app.models.sale_return import SaleReturn, SaleReturnItem
from app.models.user import User as AccountUser
from app.models.user import User, UserRole
from app.schemas.commerce import SaleCreate, SaleReturnCreate
from app.services.commerce import (
    checkout,
    list_sales,
    process_return,
    remove_sale_cost_details,
    sale_details,
)
from app.services.audit import record_audit

router = APIRouter(tags=["Sales"])


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _fetch_invoice_logo(url: str | None) -> BytesIO | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.port not in (None, 443) or not parsed.hostname or parsed.username or parsed.password:
        return None
    try:
        resolved = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not resolved or any(not ipaddress.ip_address(row[4][0]).is_global for row in resolved):
            return None
        request = Request(url, headers={"User-Agent": "POS-Invoice/1.0", "Accept": "image/png,image/jpeg,image/gif,image/webp"})
        opener = build_opener(_NoRedirectHandler())
        with opener.open(request, timeout=2) as response:
            if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                return None
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            return None
        image_data = BytesIO(data)
        ImageReader(image_data).getSize()
        image_data.seek(0)
        return image_data
    except Exception:
        return None


@router.get("/sales/{sale_id}/invoice/pdf")
def download_invoice_pdf(
    sale_id: UUID,
    user: AccountUser = Depends(require_permission(Permission.SALES_READ)),
    db: Session = Depends(get_db),
) -> Response:
    sale_data = sale_details(db, user.business_id, sale_id)
    business = db.scalar(select(Business).where(Business.id == user.business_id))
    customer = None
    if sale_data["customer_id"]:
        customer = db.scalar(select(Customer).where(
            Customer.id == sale_data["customer_id"],
            Customer.business_id == user.business_id,
        ))
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"Invoice {sale_data['invoice_number']}",
        author=business.business_name if business else "POS",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#24324a"), spaceAfter=5))
    styles.add(ParagraphStyle(name="BrandDetails", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=colors.HexColor("#68758a")))
    styles.add(ParagraphStyle(name="InvoiceNumber", parent=styles["Normal"], alignment=TA_RIGHT, fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.HexColor("#24324a")))
    styles.add(ParagraphStyle(name="MetaLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#78859a")))
    styles.add(ParagraphStyle(name="MetaValue", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#263348")))
    styles.add(ParagraphStyle(name="LogoInitials", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=colors.white))
    story = []
    business_name = business.business_name if business else "Business"
    currency = business.currency if business else "USD"
    contact = " | ".join(filter(None, [
        business.email if business else None,
        business.phone if business else None,
        business.address if business else None,
        business.city if business else None,
    ]))
    logo_data = _fetch_invoice_logo(business.logo if business else None)
    logo = Image(logo_data, width=0.52 * inch, height=0.52 * inch, kind="proportional") if logo_data else Paragraph(escape("".join(part[0] for part in business_name.split()[:2]).upper() or "CO"), styles["LogoInitials"])
    details = "<br/>".join(filter(None, [escape(contact), f"Tax number: {escape(business.tax_number)}" if business and business.tax_number else ""])) or "&nbsp;"
    brand = Table([[Paragraph("BUSINESS", styles["MetaLabel"])], [Paragraph(escape(business_name), styles["BrandName"])], [Paragraph(details, styles["BrandDetails"])]])
    invoice_meta = Paragraph(f"<font size='8' color='#5367df'><b>INVOICE</b></font><br/><b>{escape(sale_data['invoice_number'])}</b><br/><font size='8' color='#78859a'>{sale_data['sale_date']:%d %b %Y, %H:%M}</font>", styles["InvoiceNumber"])
    header = Table([[logo, brand, invoice_meta]], colWidths=[0.78 * inch, 4.04 * inch, 2.58 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fc")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#e5e9f1")),
        ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor("#5367df")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 13),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#5367df") if not logo_data else colors.HexColor("#f5f7fc")),
    ]))
    story.extend([header, Spacer(1, 17)])
    metadata = [
        [Paragraph(f"<b>Payment method</b><br/>{escape(', '.join(sorted({payment['payment_method'] for payment in sale_data['payments']})) or '?')}", styles["Normal"]),
         Paragraph(f"<b>Status</b><br/>{escape(sale_data['status'])}", styles["Normal"]),
         Paragraph(f"<b>Cashier</b><br/>{escape(sale_data['cashier_name'] or '—')}", styles["Normal"])],
        [Paragraph(f"<b>Customer</b><br/>{escape(sale_data['customer_name'] or 'Walk-in customer')}", styles["Normal"]),
         Paragraph(f"<b>Phone</b><br/>{escape(customer.phone if customer and customer.phone else '—')}", styles["Normal"]),
         Paragraph(f"<b>Address</b><br/>{escape(customer.address if customer and customer.address else '—')}", styles["Normal"])],
    ]
    metadata_table = Table(metadata, colWidths=[2.466 * inch] * 3)
    metadata_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#e1e6ef")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e1e6ef")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([metadata_table, Spacer(1, 18)])
    rows = [["Product", "SKU", "Qty", "Unit price", "Discount", "Tax", "Line total"]]
    rows.extend([
        [
            str(item["product_name"]),
            str(item["sku"]),
            str(item["quantity"]),
            f"{currency} {Decimal(item['unit_price']):,.2f}",
            f"{currency} {Decimal(item['discount']):,.2f}",
            f"{currency} {Decimal(item['tax']):,.2f}",
            f"{currency} {Decimal(item['line_total']):,.2f}",
        ]
        for item in sale_data["items"]
    ])
    item_table = Table(
        rows,
        repeatRows=1,
        colWidths=[width * inch for width in (1.4, 0.78, 0.47, 1.02, 1.02, 0.72, 1.99)],
    )
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#303f59")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fb")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe4ec")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([item_table, Spacer(1, 18)])
    totals = [
        ["Subtotal", f"{currency} {Decimal(sale_data['subtotal']):,.2f}"],
        ["Discount", f"{currency} {Decimal(sale_data['discount']):,.2f}"],
        ["Tax", f"{currency} {Decimal(sale_data['tax']):,.2f}"],
        ["Grand total", f"{currency} {Decimal(sale_data['total_amount']):,.2f}"],
        ["Paid", f"{currency} {Decimal(sale_data['paid_amount']):,.2f}"],
        ["Outstanding", f"{currency} {Decimal(sale_data['outstanding_amount']):,.2f}"],
        ["Payment method", ", ".join(sorted({payment["payment_method"] for payment in sale_data["payments"]})) or "—"],
    ]
    totals_table = Table(totals, colWidths=[2.0 * inch, 1.55 * inch], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#536176")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f0f3ff")),
        ("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor("#263a90")),
        ("LINEABOVE", (0, 3), (-1, 3), 0.8, colors.HexColor("#cbd3f7")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 2), 0.3, colors.HexColor("#e7ebf1")),
    ]))
    footer = business.invoice_footer if business and business.invoice_footer else "Thank you for your business."
    footer_style = ParagraphStyle(name="InvoiceFooter", parent=styles["Normal"], alignment=TA_LEFT, fontSize=8.5, leading=12, textColor=colors.HexColor("#7b8798"), borderColor=colors.HexColor("#e7ebf1"), borderWidth=0.5, borderPadding=9)
    story.extend([totals_table, Spacer(1, 24), Paragraph(escape(footer), footer_style)])
    document.build(story)
    safe_invoice = "".join(
        character for character in sale_data["invoice_number"]
        if character.isalnum() or character in "-_."
    ) or "invoice"
    return Response(
        content=stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_invoice}.pdf"'},
    )


@router.get("/returns")
def get_returns(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(SaleReturn).where(SaleReturn.business_id == user.business_id)
    if search and search.strip():
        query = f"%{search.strip()}%"
        matching_sales = select(Sale.id).where(Sale.business_id == user.business_id, Sale.invoice_number.ilike(query))
        stmt = stmt.where(or_(SaleReturn.notes.ilike(query), SaleReturn.sale_id.in_(matching_sales)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = db.scalars(stmt.order_by(SaleReturn.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    items = []
    for record in records:
        sale = db.scalar(select(Sale).where(Sale.id == record.sale_id, Sale.business_id == user.business_id))
        lines = db.scalars(select(SaleReturnItem).where(
            SaleReturnItem.return_id == record.id,
            SaleReturnItem.business_id == user.business_id,
        )).all()
        items.append({
            "id": record.id,
            "sale_id": record.sale_id,
            "invoice_number": sale.invoice_number if sale else None,
            "refund_amount": record.refund_amount,
            "notes": record.notes,
            "created_at": record.created_at,
            "items": [{"product_id": line.product_id, "quantity": line.quantity, "refund_amount": line.refund_amount} for line in lines],
        })
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/sales")
def get_sales(
    search: str | None = None,
    payment_status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(require_permission(Permission.SALES_READ)),
    db: Session = Depends(get_db),
) -> dict:
    if payment_status and payment_status not in {item.value for item in SalePaymentStatus}:
        raise HTTPException(status_code=422, detail="Invalid payment status")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    result = list_sales(db, user.business_id, search=search, payment_status_filter=payment_status, start_date=start_date, end_date=end_date, page=page, limit=limit)
    if user.role == UserRole.CASHIER:
        result["items"] = [remove_sale_cost_details(item) for item in result["items"]]
    return result


@router.post("/sales", status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, user: User = Depends(require_permission(Permission.SALES_CREATE)), db: Session = Depends(get_db)) -> dict:
    if user.role == UserRole.CASHIER and (payload.discount > 0 or any(item.discount > 0 for item in payload.items)):
        raise HTTPException(status_code=403, detail="Cashiers cannot apply discounts")
    try:
        sale = checkout(db, user, payload)
        record_audit(
            db, user.business_id, user.id, "create", "sale", sale.id,
            f"Created sale {sale.invoice_number}",
        )
        db.commit()
        db.refresh(sale)
        result = sale_details(db, user.business_id, sale.id)
        return remove_sale_cost_details(result) if user.role == UserRole.CASHIER else result
    except Exception:
        db.rollback()
        raise


@router.get("/sales/{sale_id}")
def get_sale(sale_id: UUID, user: User = Depends(require_permission(Permission.SALES_READ)), db: Session = Depends(get_db)) -> dict:
    result = sale_details(db, user.business_id, sale_id)
    return remove_sale_cost_details(result) if user.role == UserRole.CASHIER else result


@router.post("/sales/{sale_id}/returns", status_code=status.HTTP_201_CREATED)
def return_sale(
    sale_id: UUID,
    payload: SaleReturnCreate,
    user: User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        record = process_return(db, user, sale_id, payload)
        record_audit(
            db, user.business_id, user.id, "create", "sale_return", record.id,
            f"Recorded return for sale {sale_id}",
        )
        db.commit()
        db.refresh(record)
        return {
            "id": record.id,
            "business_id": record.business_id,
            "sale_id": record.sale_id,
            "refund_amount": record.refund_amount,
            "notes": record.notes,
            "created_by": record.created_by,
            "created_at": record.created_at,
            "sale": sale_details(db, user.business_id, sale_id),
        }
    except Exception:
        db.rollback()
        raise


@router.get("/sales/{sale_id}/returns")
def list_returns(
    sale_id: UUID,
    user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
    db: Session = Depends(get_db),
) -> list[dict]:
    sale = db.scalar(select(Sale).where(Sale.id == sale_id, Sale.business_id == user.business_id))
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    records = db.scalars(select(SaleReturn).where(
        SaleReturn.sale_id == sale.id, SaleReturn.business_id == user.business_id,
    ).order_by(SaleReturn.created_at.desc())).all()
    result = []
    for record in records:
        lines = db.scalars(select(SaleReturnItem).where(
            SaleReturnItem.return_id == record.id, SaleReturnItem.business_id == user.business_id,
        )).all()
        result.append({
            "id": record.id,
            "sale_id": record.sale_id,
            "refund_amount": record.refund_amount,
            "notes": record.notes,
            "created_at": record.created_at,
            "items": [{"sale_item_id": line.sale_item_id, "product_id": line.product_id, "quantity": line.quantity, "refund_amount": line.refund_amount} for line in lines],
        })
    return result
