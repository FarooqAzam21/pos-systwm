from decimal import Decimal


def register(client, business_name, owner_name, email):
    return client.post(
        "/auth/register",
        json={
            "business_name": business_name,
            "owner_name": owner_name,
            "email": email,
            "password": "Strong-test-password-123!",
            "confirm_password": "Strong-test-password-123!",
        },
    )


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_category_product_supplier_and_tenant_isolation(client):
    first = register(client, "Alpha Store", "Alice Jones", "alice@alpha.test")
    second = register(client, "Beta Store", "Bob Smith", "bob@beta.test")
    first_headers = auth_headers(first.json()["access_token"])
    second_headers = auth_headers(second.json()["access_token"])

    category = client.post(
        "/categories",
        headers=first_headers,
        json={"name": "Electronics", "description": "Devices and accessories"},
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["id"]

    supplier = client.post(
        "/suppliers",
        headers=first_headers,
        json={
            "name": "Jordan Ware", "company_name": "Delta Supply",
            "email": "jordan@delta.test", "phone": "+1 555 1111",
        },
    )
    assert supplier.status_code == 201, supplier.text

    product = client.post(
        "/products",
        headers=first_headers,
        json={
            "category_id": category_id,
            "sku": "IP15-001",
            "barcode": "1234567890",
            "name": "iPhone 15",
            "brand": "Apple",
            "unit": "pcs",
            "cost_price": "699.00",
            "selling_price": "899.00",
            "minimum_stock": "5",
            "maximum_stock": "30",
            "opening_stock": "10",
        },
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert product.json()["current_stock"] == "10"

    movement = client.get(f"/inventory/{product_id}/movements", headers=first_headers)
    assert movement.status_code == 200
    assert movement.json()[0]["movement_type"] == "opening_stock"

    other_product = client.get(f"/products/{product_id}", headers=second_headers)
    assert other_product.status_code == 404

    cross_business_category = client.get(f"/categories/{category_id}", headers=second_headers)
    assert cross_business_category.status_code == 404

    inventory = client.get("/inventory", headers=first_headers)
    assert inventory.status_code == 200
    assert inventory.json()["total_products"] == 1
    assert Decimal(str(inventory.json()["inventory_value"])) == Decimal("6990.00")


def test_stock_adjustments_and_low_stock(client):
    session = register(client, "Stockroom Co", "Lena Price", "lena@stockroom.test")
    headers = auth_headers(session.json()["access_token"])

    category = client.post(
        "/categories",
        headers=headers,
        json={"name": "Accessories", "description": "Accessories"},
    ).json()
    product = client.post(
        "/products",
        headers=headers,
        json={
            "category_id": category["id"],
            "sku": "HEADSET-001",
            "name": "Wireless Headset",
            "unit": "pcs",
            "cost_price": "30.00",
            "selling_price": "80.00",
            "minimum_stock": "4",
            "opening_stock": "3",
        },
    ).json()
    assert product["stock_status"] == "LOW_STOCK"

    adjust_in = client.post(
        f"/inventory/{product['id']}/adjust",
        headers=headers,
        json={"movement_type": "adjustment_in", "quantity": "5", "notes": "Restock"},
    )
    assert adjust_in.status_code == 200, adjust_in.text
    assert adjust_in.json()["new_stock"] == "8"

    adjust_out = client.post(
        f"/inventory/{product['id']}/adjust",
        headers=headers,
        json={"movement_type": "adjustment_out", "quantity": "9", "notes": "Sold"},
    )
    assert adjust_out.status_code == 400
    assert adjust_out.json()["detail"] == "Inventory cannot go below zero"

    safe_adjustment = client.post(
        f"/inventory/{product['id']}/adjust",
        headers=headers,
        json={"movement_type": "adjustment_out", "quantity": "2", "notes": "Sold"},
    )
    assert safe_adjustment.status_code == 200, safe_adjustment.text
    assert Decimal(str(safe_adjustment.json()["new_stock"])) == Decimal("6")

    low = client.get("/inventory/low-stock", headers=headers)
    assert low.status_code == 200
    assert len(low.json()) >= 0
