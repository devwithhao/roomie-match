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


def test_upsert_my_profile_creates_profile_when_missing(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "createprofile@example.com",
            "password": "password123",
            "display_name": "Create Profile",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    account_id = register.json()["user"]["id"]

    response = client.patch(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Nguyen Van B",
            "phone": "0902222222",
            "gender": "other",
            "avatar_url": "https://example.com/avatar2.jpg",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["id"] == account_id
    assert body["profile"]["full_name"] == "Nguyen Van B"
    assert body["profile"]["phone"] == "0902222222"
    assert body["profile"]["gender"] == "other"
    assert body["profile"]["avatar_url"] == "https://example.com/avatar2.jpg"


def test_upsert_my_profile_requires_auth(client):
    response = client.patch(
        "/api/v1/users/me/profile",
        json={"full_name": "No Auth"},
    )
    assert response.status_code == 401


def test_upsert_my_profile_creates_when_missing_full_name_required(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "missingfullname@example.com",
            "password": "password123",
            "display_name": "Missing Full Name",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]

    response = client.patch(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "phone": "0903333333",
        },
    )
    assert response.status_code == 422


def test_upsert_my_profile_updates_fields(client, db_session):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "updateprofile@example.com",
            "password": "password123",
            "display_name": "Update Profile",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    account_id = register.json()["user"]["id"]

    db_session.add(
        Profile(
            account_id=account_id,
            full_name="Old Name",
            phone="0900000000",
            gender="female",
            avatar_url="https://example.com/old.jpg",
        )
    )
    db_session.commit()

    response = client.patch(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "New Name",
            "phone": "0911111111",
            "avatar_url": "https://example.com/new.jpg",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["full_name"] == "New Name"
    assert body["profile"]["phone"] == "0911111111"
    assert body["profile"]["gender"] == "female"
    assert body["profile"]["avatar_url"] == "https://example.com/new.jpg"


def test_upsert_my_profile_requires_at_least_one_field_when_profile_exists(client, db_session):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "emptyupdateprofile@example.com",
            "password": "password123",
            "display_name": "Empty Update Profile",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    account_id = register.json()["user"]["id"]

    db_session.add(
        Profile(
            account_id=account_id,
            full_name="Any Name",
        )
    )
    db_session.commit()

    response = client.patch(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert response.status_code == 422


def test_upsert_my_profile_rejects_invalid_gender(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalidgender@example.com",
            "password": "password123",
            "display_name": "Invalid Gender",
            "account_type": "tenant",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]

    response = client.patch(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Lang",
            "gender": "string",
        },
    )
    assert response.status_code == 422
