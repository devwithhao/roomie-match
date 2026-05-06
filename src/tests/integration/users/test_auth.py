from __future__ import annotations


def test_register_then_login(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "password123",
            "display_name": "Alice",
            "account_type": "tenant",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["display_name"] == "Alice"
    assert body["user"]["account_type"] == "tenant"
    assert body["user"]["email_verified"] is False

    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert r2.status_code == 200
    assert r2.json()["user"]["email"] == "user@example.com"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alice"


def test_login_invalid_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "u2@example.com",
            "password": "password123",
            "display_name": "Bob",
            "account_type": "landlord",
        },
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "u2@example.com", "password": "wrong-password"},
    )
    assert r.status_code == 401


def test_duplicate_email_returns_409(client):
    payload = {
        "email": "dup@example.com",
        "password": "password123",
        "display_name": "C1",
        "account_type": "tenant",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    r2 = client.post(
        "/api/v1/auth/register",
        json={**payload, "display_name": "C2"},
    )
    assert r2.status_code == 409
