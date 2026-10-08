from uuid import UUID

from app.core.security import create_access_token, hash_password
from app.database.session import get_db
from app.main import app
from app.models.user import User, UserRole


def make_role_headers(client, owner_headers, role):
    owner = client.get("/auth/me", headers=owner_headers).json()
    database = app.dependency_overrides[get_db]()
    session = next(database)
    user = User(
        name=f"Day Three {role.value}",
        email=f"{role.value.lower()}@day3-permissions.test",
        password_hash=hash_password("test-password-long-enough"),
        role=role,
        business_id=UUID(owner["business_id"]),
        is_active=True,
    )
    session.add(user)
    session.commit()
    token = create_access_token(user.id)
    database.close()
    return {"Authorization": f"Bearer {token}"}


def test_cashier_management_permissions_and_dashboard(client):
    registered = client.post("/auth/register", json={
        "business_name": "Day Three Permission Store",
        "owner_name": "Permission Owner",
        "email": "owner@day3-permissions.test",
        "password": "Strong-test-password-123!",
        "confirm_password": "Strong-test-password-123!",
    })
    assert registered.status_code == 201, registered.text
    owner_headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    cashier_headers = make_role_headers(client, owner_headers, UserRole.CASHIER)
    admin_headers = make_role_headers(client, owner_headers, UserRole.ADMIN)

    restricted_reads = (
        "/expenses",
        "/expenses/categories",
        "/reports/sales",
        "/reports/profit-and-loss",
        "/reports/sales/export.xlsx",
        "/audit-logs",
        "/purchases",
        "/suppliers",
        "/payments",
        "/users",
        "/inventory",
        "/inventory/low-stock",
    )
    for path in restricted_reads:
        response = client.get(path, headers=cashier_headers)
        assert response.status_code == 403, f"{path}: {response.status_code} {response.text}"

    settings_response = client.put("/business", headers=cashier_headers, json={
        "business_name": "Unauthorized Change",
        "owner_name": "Permission Owner",
        "email": "owner@day3-permissions.test",
        "currency": "USD",
        "timezone": "UTC",
    })
    assert settings_response.status_code == 403, settings_response.text

    dashboard = client.get("/dashboard/overview", headers=cashier_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert set(dashboard.json()) == {"today", "sales_trend"}
    assert client.get("/dashboard/overview", headers=owner_headers).status_code == 200

    product = client.post("/products", headers=owner_headers, json={
        "sku": "CASHIER-ITEM",
        "name": "Cashier Item",
        "unit": "pcs",
        "cost_price": "10",
        "selling_price": "20",
        "opening_stock": "2",
    })
    assert product.status_code == 201, product.text
    cashier_product = client.get(f"/products/{product.json()['id']}", headers=cashier_headers)
    assert cashier_product.status_code == 200
    assert not {"cost_price", "inventory_value", "unit_profit", "margin_percentage"} & set(cashier_product.json())

    cashier_sale = client.post("/sales", headers=cashier_headers, json={
        "paid_amount": "20",
        "items": [{"product_id": product.json()["id"], "quantity": "1"}],
    })
    assert cashier_sale.status_code == 201, cashier_sale.text
    assert not {"cogs_amount", "gross_profit"} & set(cashier_sale.json())
    cashier_detail = client.get(f"/sales/{cashier_sale.json()['id']}", headers=cashier_headers)
    assert cashier_detail.status_code == 200
    assert not {"cogs_amount", "gross_profit"} & set(cashier_detail.json())
    assert not {"unit_cost", "cogs", "gross_profit"} & set(cashier_detail.json()["items"][0])
    assert client.get(f"/sales/{cashier_sale.json()['id']}/returns", headers=cashier_headers).status_code == 403

    created = client.post("/users", headers=owner_headers, json={
        "name": "Managed User",
        "email": "managed-user@day3-permissions.test",
        "password": "Secret-user-password-123!",
        "role": "Cashier",
    })
    assert created.status_code == 201, created.text
    assert "password_hash" not in created.json()
    updated = client.put(f"/users/{created.json()['id']}", headers=owner_headers, json={"role": "Manager"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == "Manager"

    owner_escalation = client.post("/users", headers=admin_headers, json={
        "name": "Extra Owner",
        "email": "extra-owner@day3-permissions.test",
        "password": "Secret-owner-password-123!",
        "role": "Owner",
    })
    assert owner_escalation.status_code == 403, owner_escalation.text
    audit_rows = client.get("/audit-logs", headers=owner_headers).json()["items"]
    role_event = next(row for row in audit_rows if row["entity_id"] == created.json()["id"])
    assert "changed role from Cashier to Manager" in role_event["description"]
    assert "password" not in role_event["description"].lower()
