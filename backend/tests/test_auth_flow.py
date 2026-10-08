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


def test_registration_settings_login_and_tenant_isolation(client):
    first_registration = register(
        client, "Northstar Market", "Jamie Davis", "JAMIE@example.com"
    )
    assert first_registration.status_code == 201
    first_session = first_registration.json()
    first_user = first_session["user"]
    assert first_user["role"] == "Owner"
    assert first_user["business_name"] == "Northstar Market"
    assert "password" not in first_user
    first_headers = {"Authorization": f"Bearer {first_session['access_token']}"}

    business_response = client.get("/business", headers=first_headers)
    assert business_response.status_code == 200
    assert business_response.json()["business_name"] == "Northstar Market"

    updated_profile = client.put(
        "/business",
        headers=first_headers,
        json={
            "business_name": "Northstar Downtown",
            "owner_name": "Jamie Davis",
            "email": "store@example.com",
            "phone": "+1 555 0100",
            "address": "12 Harbor Avenue",
            "currency": "USD",
            "timezone": "UTC",
            "logo": None,
        },
    )
    assert updated_profile.status_code == 200
    assert updated_profile.json()["business_name"] == "Northstar Downtown"

    second_registration = register(
        client, "Harbor Goods", "Morgan Lee", "morgan@example.com"
    )
    assert second_registration.status_code == 201
    second_user_id = second_registration.json()["user"]["id"]
    hidden_user = client.get(f"/users/{second_user_id}", headers=first_headers)
    assert hidden_user.status_code == 404
    own_users = client.get("/users", headers=first_headers)
    assert own_users.status_code == 200
    assert [entry["email"] for entry in own_users.json()] == ["jamie@example.com"]

    login = client.post(
        "/auth/login",
        json={"email": "jamie@example.com", "password": "Strong-test-password-123!"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["business_id"] == first_user["business_id"]
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "jamie@example.com"


def test_authentication_and_role_protection(client):
    assert client.get("/business").status_code == 401
    session = register(client, "Owner Store", "Owner Person", "owner@example.com").json()
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    assert client.put(
        "/business",
        headers=headers,
        json={
            "business_name": "Owner Store",
            "owner_name": "Owner Person",
            "email": "owner@example.com",
            "currency": "USD",
            "timezone": "UTC",
        },
    ).status_code == 200
    assert client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "incorrect-password"},
    ).status_code == 401
