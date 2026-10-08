from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.session import get_db
from app.main import app
from app.models.sale import Sale


def test_reports_respect_today_yesterday_and_custom_ranges(client):
    suffix = uuid4().hex[:10]
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    registration = client.post("/auth/register", json={
        "business_name": f"Date Filter Store {suffix}",
        "owner_name": "Date Filter Owner",
        "email": f"date-filter-{suffix}@day3.test",
        "password": "Strong-test-password-123!",
        "confirm_password": "Strong-test-password-123!",
    })
    assert registration.status_code == 201, registration.text
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

    supplier = client.post("/suppliers", headers=headers, json={"name": "Date Filter Supplier"})
    assert supplier.status_code == 201, supplier.text
    category = client.post("/categories", headers=headers, json={"name": "Date Filter Category"})
    assert category.status_code == 201, category.text
    product = client.post("/products", headers=headers, json={
        "category_id": category.json()["id"],
        "sku": f"DATE-{suffix}",
        "name": "Date Filter Product",
        "unit": "pcs",
        "cost_price": "10",
        "selling_price": "20",
        "opening_stock": "0",
    })
    assert product.status_code == 201, product.text

    for invoice, purchase_date in ((f"T-{suffix}", today), (f"Y-{suffix}", yesterday)):
        response = client.post("/purchases", headers=headers, json={
            "supplier_id": supplier.json()["id"],
            "invoice_number": invoice,
            "purchase_date": purchase_date.isoformat(),
            "items": [{"product_id": product.json()["id"], "quantity": "2", "unit_cost": "10"}],
        })
        assert response.status_code == 201, response.text

    sales = []
    for _ in range(2):
        response = client.post("/sales", headers=headers, json={
            "paid_amount": "20",
            "items": [{"product_id": product.json()["id"], "quantity": "1"}],
        })
        assert response.status_code == 201, response.text
        sales.append(response.json())

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    old_sale = db.scalar(select(Sale).where(Sale.id == UUID(sales[0]["id"])))
    old_sale.sale_date = datetime.combine(yesterday, time(hour=12), tzinfo=timezone.utc)
    db.commit()
    db_generator.close()

    rent = next(
        row for row in client.get("/expenses/categories", headers=headers).json()
        if row["name"] == "Rent"
    )
    for expense_date, amount in ((today, "5"), (yesterday, "8")):
        response = client.post("/expenses", headers=headers, json={
            "category_id": rent["id"],
            "description": "Date filter expense",
            "amount": amount,
            "expense_date": expense_date.isoformat(),
            "payment_method": "cash",
        })
        assert response.status_code == 201, response.text

    date_ranges = (
        (today, today, 1),
        (yesterday, yesterday, 1),
        (yesterday, today, 2),
    )
    for start, end, expected_count in date_ranges:
        params = {"start_date": start.isoformat(), "end_date": end.isoformat()}
        assert client.get("/reports/sales", headers=headers, params=params).json()["total"] == expected_count
        assert client.get("/reports/purchases", headers=headers, params=params).json()["total"] == expected_count
        assert client.get("/reports/expenses", headers=headers, params=params).json()["total"] == expected_count
        pnl = client.get("/reports/profit-and-loss", headers=headers, params=params).json()
        assert Decimal(str(pnl["net_revenue"])) == Decimal("20.00") * expected_count
        if start == end:
            closing = client.get(
                "/reports/daily-closing",
                headers=headers,
                params={"report_date": start.isoformat()},
            ).json()
            assert closing["summary"]["transactions"] == expected_count
