def register_owner(client, business, email):
    response = client.post("/auth/register", json={
        "business_name": business,
        "owner_name": "Workspace Owner",
        "email": email,
        "password": "Strong-test-password-123!",
        "confirm_password": "Strong-test-password-123!",
    })
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_staff(client, headers, email="new.cashier@gmail.com", role="Cashier"):
    response = client.post("/users", headers=headers, json={
        "name": "New Cashier",
        "email": email,
        "password": "Temp-Password-123!",
        "role": role,
    })
    assert response.status_code == 201, response.text
    return response.json()


def activate_staff(client, owner_headers, staff, new_password="Activated-Password-123!"):
    login = client.post("/auth/login", json={"email": staff["email"], "password": "Temp-Password-123!"})
    assert login.json().get("activation_required") is True
    request_id = login.json()["request_id"]
    otp_response = client.post(f"/users/activation-requests/{request_id}/otp", headers=owner_headers)
    assert otp_response.status_code == 200, otp_response.text
    challenge = client.post("/auth/activation/verify", json={
        "request_id": request_id, "otp": otp_response.json()["otp"],
    }).json()["challenge_token"]
    complete = client.post("/auth/activation/password", json={
        "challenge_token": challenge, "new_password": new_password,
    })
    assert complete.status_code == 200, complete.text
    return {"Authorization": f"Bearer {complete.json()['access_token']}"}


def test_owner_approved_first_activation_and_single_use_otp(client):
    owner_headers = register_owner(client, "Activation Store", "activation-owner@example.com")
    other_owner = register_owner(client, "Other Store", "other-owner@example.com")
    staff = create_staff(client, owner_headers)

    login = client.post("/auth/login", json={"email": staff["email"], "password": "Temp-Password-123!"})
    assert login.status_code == 200
    assert login.json()["activation_required"] is True
    request_id = login.json()["request_id"]
    assert "access_token" not in login.json()
    assert client.get("/auth/me").status_code == 401

    pending = client.get("/users/activation-requests", headers=owner_headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert pending.json()[0]["id"] == request_id
    assert client.get("/users/activation-requests", headers=other_owner).json() == []
    assert client.post(f"/users/activation-requests/{request_id}/otp", headers=other_owner).status_code == 404

    issued = client.post(f"/users/activation-requests/{request_id}/otp", headers=owner_headers)
    assert issued.status_code == 200
    assert issued.headers["cache-control"] == "no-store, private"
    code = issued.json()["otp"]
    assert len(code) == 6 and code.isdigit()
    assert client.get(f"/users/activation-requests/{request_id}/otp", headers=owner_headers).json()["otp"] == code

    invalid = client.post("/auth/activation/verify", json={"request_id": request_id, "otp": "000000" if code != "000000" else "000001"})
    assert invalid.status_code == 400
    verified = client.post("/auth/activation/verify", json={"request_id": request_id, "otp": code})
    assert verified.status_code == 200
    challenge = verified.json()["challenge_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {challenge}"}).status_code == 401
    assert client.post("/auth/activation/verify", json={"request_id": request_id, "otp": code}).status_code == 400

    activated = client.post("/auth/activation/password", json={
        "challenge_token": challenge,
        "new_password": "Changed-Password-456!",
    })
    assert activated.status_code == 200, activated.text
    staff_headers = {"Authorization": f"Bearer {activated.json()['access_token']}"}
    assert client.get("/auth/me", headers=staff_headers).status_code == 200
    assert activated.json()["user"]["is_activated"] is True
    assert activated.json()["user"]["must_change_password"] is False

    subsequent = client.post("/auth/login", json={"email": staff["email"], "password": "Changed-Password-456!"})
    assert subsequent.status_code == 200
    assert "access_token" in subsequent.json()

    reset = client.post(f"/users/{staff['id']}/password-reset", headers=owner_headers)
    assert reset.status_code == 200
    assert reset.headers["cache-control"] == "no-store, private"
    assert client.get("/auth/me", headers=staff_headers).status_code == 401
    reset_login = client.post("/auth/login", json={"email": staff["email"], "password": reset.json()["temporary_password"]})
    assert reset_login.status_code == 200
    assert reset_login.json()["password_change_required"] is True
    reset_complete = client.post("/auth/activation/password", json={
        "challenge_token": reset_login.json()["challenge_token"],
        "new_password": "Reset-Password-789!",
    })
    assert reset_complete.status_code == 200


def test_owner_only_staff_management_and_activation_identity(client):
    owner_headers = register_owner(client, "Role Store", "role-owner@example.com")
    staff = create_staff(client, owner_headers, email="inventory.staff@gmail.com", role="Inventory Manager")
    other_owner = register_owner(client, "Second Store", "second-owner@example.com")
    other_users = client.get("/users", headers=other_owner).json()
    assert len(other_users) == 1
    assert all(item["id"] != staff["id"] for item in other_users)
    assert client.put(f"/users/{staff['id']}", headers=other_owner, json={"role": "Cashier"}).status_code == 404
    inv_headers = activate_staff(client, owner_headers, staff)
    assert client.get("/reports/sales", headers=inv_headers).status_code == 403
    assert client.get("/users", headers=inv_headers).status_code == 403
    allowed_product = client.post("/products", headers=inv_headers, json={
        "sku": "INVMANAGER-ITEM", "name": "Authorized product", "unit": "pcs",
        "cost_price": "5", "selling_price": "10", "opening_stock": "3",
    })
    assert allowed_product.status_code == 201, allowed_product.text
    assert client.post("/users", headers=inv_headers, json={
        "name": "Escalation attempt", "email": "escalation@gmail.com",
        "password": "Temp-Password-123!", "role": "Owner",
    }).status_code == 403

    cashier = create_staff(client, owner_headers, email="cashier.staff@gmail.com", role="Cashier")
    cash_headers = activate_staff(client, owner_headers, cashier)
    assert client.post("/products", headers=cash_headers, json={
        "sku": "DENIED", "name": "Forbidden product", "unit": "pcs",
        "selling_price": "10", "opening_stock": "1",
    }).status_code == 403
    assert client.get("/inventory", headers=cash_headers).status_code == 403
