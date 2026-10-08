from decimal import Decimal


def register(client, business_name, name, email):
    return client.post("/auth/register", json={
        "business_name": business_name,
        "owner_name": name,
        "email": email,
        "password": "Strong-test-password-123!",
        "confirm_password": "Strong-test-password-123!",
    })


def headers(response):
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_inventory(client, auth):
    supplier_response = client.post("/suppliers", headers=auth, json={"name": "Parts Supplier"})
    assert supplier_response.status_code == 201, supplier_response.text
    category_response = client.post("/categories", headers=auth, json={"name": "Hardware"})
    assert category_response.status_code == 201, category_response.text
    product_response = client.post("/products", headers=auth, json={
        "category_id": category_response.json()["id"],
        "sku": "WIDGET-1",
        "name": "Widget",
        "unit": "pcs",
        "cost_price": "100",
        "selling_price": "150",
        "minimum_stock": "2",
        "opening_stock": "0",
    })
    assert product_response.status_code == 201, product_response.text
    return supplier_response.json(), product_response.json()


def test_purchase_checkout_payment_return_and_dashboard(client):
    auth = headers(register(client, "Commerce Store", "Casey Owner", "casey@commerce.test"))
    supplier, product = create_inventory(client, auth)
    customer_response = client.post("/customers", headers=auth, json={
        "name": "Taylor Customer",
        "phone": "555-0100",
    })
    assert customer_response.status_code == 201, customer_response.text
    customer_id = customer_response.json()["id"]
    product_id = product["id"]

    purchase = client.post("/purchases", headers=auth, json={
        "supplier_id": supplier["id"],
        "invoice_number": "SUP-100",
        "paid_amount": "400",
        "items": [{"product_id": product_id, "quantity": "10", "unit_cost": "100"}],
    })
    assert purchase.status_code == 201, purchase.text
    assert Decimal(str(purchase.json()["outstanding_amount"])) == Decimal("600.00")
    assert purchase.json()["payment_status"] == "partial"
    supplier_balance = client.get("/suppliers", headers=auth).json()
    assert Decimal(str(supplier_balance[0]["outstanding_balance"])) == Decimal("600.00")
    supplier_payment = client.post("/payments/supplier", headers=auth, json={
        "purchase_id": purchase.json()["id"],
        "amount": "200",
        "payment_method": "bank_transfer",
        "reference_number": "BANK-1",
    })
    assert supplier_payment.status_code == 201, supplier_payment.text
    assert Decimal(str(client.get("/suppliers", headers=auth).json()[0]["outstanding_balance"])) == Decimal("400.00")
    purchase_detail = client.get(f"/purchases/{purchase.json()['id']}", headers=auth)
    assert purchase_detail.status_code == 200, purchase_detail.text
    assert Decimal(str(purchase_detail.json()["outstanding_amount"])) == Decimal("400.00")
    assert len(purchase_detail.json()["stock_movements"]) == 1
    assert len(purchase_detail.json()["payments"]) == 2
    assert any(
        payment["supplier_name"] == "Parts Supplier"
        for payment in client.get("/payments", headers=auth).json()
    )

    product_after_purchase = client.get(f"/products/{product_id}", headers=auth).json()
    assert Decimal(str(product_after_purchase["current_stock"])) == Decimal("10")
    assert Decimal(str(product_after_purchase["cost_price"])) == Decimal("100")
    purchase_movements = client.get(f"/inventory/{product_id}/movements", headers=auth).json()
    assert purchase_movements[0]["movement_type"] == "purchase"

    sale = client.post("/sales", headers=auth, json={
        "customer_id": customer_id,
        "paid_amount": "200",
        "items": [{"product_id": product_id, "quantity": "2"}],
    })
    assert sale.status_code == 201, sale.text
    sale_data = sale.json()
    assert Decimal(str(sale_data["total_amount"])) == Decimal("300.00")
    assert Decimal(str(sale_data["paid_amount"])) == Decimal("200.00")
    assert Decimal(str(sale_data["outstanding_amount"])) == Decimal("100.00")
    assert Decimal(str(sale_data["cogs_amount"])) == Decimal("200.00")
    assert Decimal(str(sale_data["gross_profit"])) == Decimal("100.00")
    assert Decimal(str(client.get(f"/products/{product_id}", headers=auth).json()["current_stock"])) == Decimal("8")
    sale_movements = client.get(f"/inventory/{product_id}/movements", headers=auth).json()
    assert sale_movements[0]["movement_type"] == "sale"
    assert Decimal(str(client.get(f"/customers/{customer_id}", headers=auth).json()["current_balance"])) == Decimal("100.00")
    invoice_pdf = client.get(f"/sales/{sale_data['id']}/invoice/pdf", headers=auth)
    assert invoice_pdf.status_code == 200, invoice_pdf.text
    assert invoice_pdf.headers["content-type"] == "application/pdf"
    assert invoice_pdf.content.startswith(b"%PDF-")
    assert len(invoice_pdf.content) > 1000

    too_much_payment = client.post("/payments/customer", headers=auth, json={
        "customer_id": customer_id, "amount": "101", "payment_method": "cash",
    })
    assert too_much_payment.status_code == 422
    receipt = client.post("/payments/customer", headers=auth, json={
        "customer_id": customer_id, "amount": "100", "payment_method": "cash",
    })
    assert receipt.status_code == 201, receipt.text
    assert Decimal(str(client.get(f"/customers/{customer_id}", headers=auth).json()["current_balance"])) == Decimal("0")
    customer_details = client.get(f"/customers/{customer_id}", headers=auth).json()
    assert customer_details["transaction_count"] == 1

    detail = client.get(f"/sales/{sale_data['id']}", headers=auth).json()
    returned = client.post(f"/sales/{sale_data['id']}/returns", headers=auth, json={
        "items": [{"sale_item_id": detail["items"][0]["id"], "quantity": "1"}],
        "payment_method": "cash",
    })
    assert returned.status_code == 201, returned.text
    assert Decimal(str(returned.json()["refund_amount"])) == Decimal("150.00")
    assert returned.json()["sale"]["status"] == "partially_returned"
    assert Decimal(str(returned.json()["sale"]["total_amount"])) == Decimal("150.00")
    assert Decimal(str(returned.json()["sale"]["gross_profit"])) == Decimal("50.00")
    assert Decimal(str(client.get(f"/products/{product_id}", headers=auth).json()["current_stock"])) == Decimal("9")
    assert Decimal(str(client.get(f"/customers/{customer_id}", headers=auth).json()["current_balance"])) == Decimal("0")
    return_history = client.get("/returns", headers=auth)
    assert return_history.status_code == 200, return_history.text
    assert return_history.json()["total"] == 1
    customer_details = client.get(f"/customers/{customer_id}", headers=auth).json()
    assert customer_details["returns"][0]["invoice_number"] == sale_data["invoice_number"]
    assert customer_details["returns"][0]["items"][0]["product_name"] == "Widget"

    over_return = client.post(f"/sales/{sale_data['id']}/returns", headers=auth, json={
        "items": [{"sale_item_id": detail["items"][0]["id"], "quantity": "2"}],
    })
    assert over_return.status_code == 422

    dashboard = client.get("/dashboard/overview", headers=auth)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["today"]["transactions"] == 1
    assert Decimal(str(dashboard.json()["today"]["sales"])) == Decimal("150.00")
    assert Decimal(str(dashboard.json()["today"]["gross_profit"])) == Decimal("50.00")
    assert Decimal(str(dashboard.json()["top_products"][0]["revenue"])) == Decimal("150.00")


def test_purchase_weighted_average_and_failed_checkout_atomicity(client):
    auth = headers(register(client, "Costing Store", "Morgan Owner", "morgan@costing.test"))
    supplier, product = create_inventory(client, auth)
    product_id = product["id"]
    for invoice, cost in (("COST-1", "100"), ("COST-2", "120")):
        response = client.post("/purchases", headers=auth, json={
            "supplier_id": supplier["id"],
            "invoice_number": invoice,
            "items": [{"product_id": product_id, "quantity": "10", "unit_cost": cost}],
        })
        assert response.status_code == 201, response.text
    product_after = client.get(f"/products/{product_id}", headers=auth).json()
    assert Decimal(str(product_after["current_stock"])) == Decimal("20")
    assert Decimal(str(product_after["cost_price"])) == Decimal("110.00")

    historical_sale = client.post("/sales", headers=auth, json={
        "paid_amount": "150",
        "items": [{"product_id": product_id, "quantity": "1"}],
    })
    assert historical_sale.status_code == 201, historical_sale.text
    later_purchase = client.post("/purchases", headers=auth, json={
        "supplier_id": supplier["id"],
        "invoice_number": "COST-3",
        "items": [{"product_id": product_id, "quantity": "10", "unit_cost": "130"}],
    })
    assert later_purchase.status_code == 201, later_purchase.text
    historical_detail = client.get(f"/sales/{historical_sale.json()['id']}", headers=auth).json()
    assert Decimal(str(historical_detail["items"][0]["unit_cost"])) == Decimal("110.00")

    insufficient = client.post("/sales", headers=auth, json={
        "items": [{"product_id": product_id, "quantity": "30"}],
    })
    assert insufficient.status_code == 409
    assert Decimal(str(client.get(f"/products/{product_id}", headers=auth).json()["current_stock"])) == Decimal("29")
    sales = client.get("/sales", headers=auth).json()
    assert sales["total"] == 1
    assert len(client.get(f"/inventory/{product_id}/movements", headers=auth).json()) == 4
    assert len(client.get("/payments", headers=auth).json()) == 1


def test_customer_updates_and_financial_statuses(client):
    auth = headers(register(client, "Customer Flow", "Sam Owner", "sam@customer-flow.test"))
    supplier, product = create_inventory(client, auth)
    customer = client.post("/customers", headers=auth, json={"name": "Initial Name"})
    assert customer.status_code == 201, customer.text
    customer_id = customer.json()["id"]
    updated = client.put(f"/customers/{customer_id}", headers=auth, json={
        "name": "Updated Name",
        "email": "updated@example.test",
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated Name"
    assert updated.json()["email"] == "updated@example.test"
    forged_balance = client.put(f"/customers/{customer_id}", headers=auth, json={"current_balance": "0"})
    assert forged_balance.status_code == 422

    purchase = client.post("/purchases", headers=auth, json={
        "supplier_id": supplier["id"],
        "invoice_number": "FULL-RETURN-STOCK",
        "items": [{"product_id": product["id"], "quantity": "10", "unit_cost": "100"}],
    })
    assert purchase.status_code == 201, purchase.text
    full_sale = client.post("/sales", headers=auth, json={
        "customer_id": customer_id,
        "paid_amount": "1500",
        "items": [{"product_id": product["id"], "quantity": "10"}],
    })
    assert full_sale.status_code == 201, full_sale.text
    sale_data = full_sale.json()
    assert Decimal(str(sale_data["total_amount"])) == Decimal("1500.00")
    assert Decimal(str(sale_data["cogs_amount"])) == Decimal("1000.00")
    assert Decimal(str(sale_data["gross_profit"])) == Decimal("500.00")

    partial_return = client.post(f"/sales/{sale_data['id']}/returns", headers=auth, json={
        "items": [{"sale_item_id": sale_data["items"][0]["id"], "quantity": "3"}],
    })
    assert partial_return.status_code == 201, partial_return.text
    assert partial_return.json()["sale"]["status"] == "partially_returned"
    full_return = client.post(f"/sales/{sale_data['id']}/returns", headers=auth, json={
        "items": [{"sale_item_id": sale_data["items"][0]["id"], "quantity": "7"}],
    })
    assert full_return.status_code == 201, full_return.text
    assert full_return.json()["sale"]["status"] == "returned"
    assert Decimal(str(full_return.json()["sale"]["total_amount"])) == Decimal("0.00")
    assert Decimal(str(client.get(f"/products/{product['id']}", headers=auth).json()["current_stock"])) == Decimal("10")

    adjusted_sale = client.post("/sales", headers=auth, json={
        "customer_id": customer_id,
        "paid_amount": "276",
        "discount": "30",
        "tax": "6",
        "items": [{"product_id": product["id"], "quantity": "2"}],
    })
    assert adjusted_sale.status_code == 201, adjusted_sale.text
    adjusted_return = client.post(f"/sales/{adjusted_sale.json()['id']}/returns", headers=auth, json={
        "items": [{"sale_item_id": adjusted_sale.json()["items"][0]["id"], "quantity": "1"}],
    })
    assert adjusted_return.status_code == 201, adjusted_return.text
    assert Decimal(str(adjusted_return.json()["refund_amount"])) == Decimal("138.00")
    assert Decimal(str(adjusted_return.json()["sale"]["total_amount"])) == Decimal("138.00")
    adjusted_dashboard = client.get("/dashboard/overview", headers=auth)
    assert Decimal(str(adjusted_dashboard.json()["top_products"][0]["revenue"])) == Decimal("138.00")

    rounding_sale = client.post("/sales", headers=auth, json={
        "customer_id": customer_id,
        "paid_amount": "449",
        "discount": "1",
        "items": [{"product_id": product["id"], "quantity": "3"}],
    })
    assert rounding_sale.status_code == 201, rounding_sale.text
    refund_amounts = []
    for _ in range(3):
        rounding_detail = client.get(f"/sales/{rounding_sale.json()['id']}", headers=auth).json()
        refund = client.post(f"/sales/{rounding_sale.json()['id']}/returns", headers=auth, json={
            "items": [{"sale_item_id": rounding_detail["items"][0]["id"], "quantity": "1"}],
        })
        assert refund.status_code == 201, refund.text
        refund_amounts.append(Decimal(str(refund.json()["refund_amount"])))
    assert sum(refund_amounts) == Decimal("449.00")
    assert refund.json()["sale"]["status"] == "returned"
    assert Decimal(str(refund.json()["sale"]["total_amount"])) == Decimal("0.00")

    unpaid_sale = client.post("/sales", headers=auth, json={
        "customer_id": customer_id,
        "items": [{"product_id": product["id"], "quantity": "1"}],
    })
    assert unpaid_sale.status_code == 201, unpaid_sale.text
    assert unpaid_sale.json()["payment_status"] == "unpaid"
    assert Decimal(str(client.get(f"/customers/{customer_id}", headers=auth).json()["current_balance"])) == Decimal("150.00")

    partial_payment = client.post("/payments/customer", headers=auth, json={
        "customer_id": customer_id, "amount": "50", "payment_method": "cash",
    })
    assert partial_payment.status_code == 201, partial_payment.text
    sale_after_partial = client.get(f"/sales/{unpaid_sale.json()['id']}", headers=auth).json()
    assert sale_after_partial["payment_status"] == "partial"
    assert Decimal(str(sale_after_partial["outstanding_amount"])) == Decimal("100.00")
    full_payment = client.post("/payments/customer", headers=auth, json={
        "customer_id": customer_id, "amount": "100", "payment_method": "card",
    })
    assert full_payment.status_code == 201, full_payment.text
    assert client.get(f"/sales/{unpaid_sale.json()['id']}", headers=auth).json()["payment_status"] == "paid"
    assert Decimal(str(client.get(f"/customers/{customer_id}", headers=auth).json()["current_balance"])) == Decimal("0.00")


def test_commerce_records_are_tenant_isolated(client):
    business_a = headers(register(client, "Tenant A", "Alex Owner", "alex@tenant-a.test"))
    business_b = headers(register(client, "Tenant B", "Blair Owner", "blair@tenant-b.test"))
    supplier, product = create_inventory(client, business_a)
    customer = client.post("/customers", headers=business_a, json={"name": "A Customer"}).json()
    purchase = client.post("/purchases", headers=business_a, json={
        "supplier_id": supplier["id"],
        "invoice_number": "TENANT-A-1",
        "items": [{"product_id": product["id"], "quantity": "1", "unit_cost": "100"}],
    }).json()
    sale = client.post("/sales", headers=business_a, json={
        "customer_id": customer["id"],
        "items": [{"product_id": product["id"], "quantity": "1"}],
    })
    assert sale.status_code == 201, sale.text
    returned = client.post(f"/sales/{sale.json()['id']}/returns", headers=business_a, json={
        "items": [{"sale_item_id": sale.json()["items"][0]["id"], "quantity": "1"}],
    })
    assert returned.status_code == 201, returned.text

    assert client.get(f"/customers/{customer['id']}", headers=business_b).status_code == 404
    assert client.get(f"/purchases/{purchase['id']}", headers=business_b).status_code == 404
    assert client.get(f"/sales/{sale.json()['id']}", headers=business_b).status_code == 404
    assert client.get(f"/products/{product['id']}", headers=business_b).status_code == 404
    assert client.get(f"/sales/{sale.json()['id']}/invoice/pdf", headers=business_b).status_code == 404
    assert client.get(f"/purchases/{purchase['id']}", headers=business_b).status_code == 404
    cross_tenant_supplier_payment = client.post("/payments/supplier", headers=business_b, json={
        "purchase_id": purchase["id"],
        "amount": "1",
        "payment_method": "cash",
    })
    assert cross_tenant_supplier_payment.status_code == 404
    assert client.get(f"/inventory/{product['id']}/movements", headers=business_b).status_code == 404
    assert client.get("/customers", headers=business_b).json()["total"] == 0
    assert client.get("/sales", headers=business_b).json()["total"] == 0
    assert client.get("/purchases", headers=business_b).json()["total"] == 0
    assert client.get("/payments", headers=business_b).json() == []
    assert client.get(f"/sales/{sale.json()['id']}/returns", headers=business_b).status_code == 404
    assert client.get("/returns", headers=business_a).json()["total"] == 1
    assert client.get("/returns", headers=business_b).json()["total"] == 0
