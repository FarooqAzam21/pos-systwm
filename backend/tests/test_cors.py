def test_vercel_login_preflight_allows_production_origin(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://pos-systwm.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://pos-systwm.vercel.app"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_cors_does_not_allow_arbitrary_origins(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
