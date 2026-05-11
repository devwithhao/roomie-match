from __future__ import annotations

from app.models.users.profile import Profile


def test_get_my_profile_returns_account_and_profile(client, db_session):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@example.com",
            "password": "password123",
            "display_name": "Profile User",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    account_id = register.json()["user"]["id"]

    db_session.add(
        Profile(
            account_id=account_id,
            full_name="Nguyen Van A",
            phone="0901234567",
            gender="male",
            avatar_url="https://example.com/avatar.jpg",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["id"] == account_id
    assert body["account"]["email"] == "profile@example.com"
    assert body["account"]["account_type"] == "tenant"
    assert body["profile"]["full_name"] == "Nguyen Van A"
    assert body["profile"]["phone"] == "0901234567"
    assert body["profile"]["gender"] == "male"


def test_get_my_profile_requires_auth(client):
    response = client.get("/api/v1/users/me/profile")
    assert response.status_code == 401


def test_get_my_profile_returns_404_when_missing(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "missingprofile@example.com",
            "password": "password123",
            "display_name": "No Profile",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]

    response = client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
