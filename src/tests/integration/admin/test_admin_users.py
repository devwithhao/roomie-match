from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role


def _role_id(db: Session, name: str) -> int:
    role = db.query(Role).filter(Role.name == name).one()
    return role.id


def _create_account(
    db: Session,
    *,
    email: str,
    username: str,
    role: str,
    status: str = "active",
    password: str = "password123",
) -> Account:
    account = Account(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role_id=_role_id(db, role),
        status=status,
    )
    db.add(account)
    db.flush()
    db.add(Profile(account_id=account.id, full_name=username))
    db.commit()
    db.refresh(account)
    return account


def _token_for(client, email: str, password: str = "password123") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_create_and_list_users(client, db_session: Session):
    _create_account(db_session, email="admin@example.com", username="admin", role="admin")
    token = _token_for(client, "admin@example.com")

    created = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "tenant_one",
            "email": "tenant.one@example.com",
            "phone": "0900000001",
            "password": "password123",
            "role": "tenant",
            "status": "active",
        },
    )

    assert created.status_code == 201
    assert created.json()["email"] == "tenant.one@example.com"

    listed = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"role": "tenant", "q": "tenant.one", "page": 1, "page_size": 6},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "tenant_one"


def test_non_admin_cannot_access_admin_users(client, db_session: Session):
    _create_account(db_session, email="tenant@example.com", username="tenant", role="tenant")
    token = _token_for(client, "tenant@example.com")

    response = client.get("/api/v1/admin/users/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_blocked_user_cannot_login(client, db_session: Session):
    _create_account(db_session, email="admin@example.com", username="admin", role="admin")
    user = _create_account(db_session, email="blocked.target@example.com", username="blocked_target", role="tenant")
    token = _token_for(client, "admin@example.com")

    blocked = client.patch(
        f"/api/v1/admin/users/{user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "blocked"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "blocked.target@example.com", "password": "password123"},
    )
    assert login.status_code == 401


def test_cannot_block_last_active_admin(client, db_session: Session):
    admin = _create_account(db_session, email="admin@example.com", username="admin", role="admin")
    token = _token_for(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/admin/users/{admin.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "blocked"},
    )

    assert response.status_code == 409

