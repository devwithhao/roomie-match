import pytest
from sqlalchemy.orm import Session

from app.features.packages.models import Package
from app.features.users.models import Account, Role


@pytest.fixture
def admin_user(db_session: Session):
    role = db_session.query(Role).filter(Role.name == "admin").first()
    if not role:
        role = Role(name="admin", description="Admin role")
        db_session.add(role)
        db_session.flush()

    user = Account(
        email="admin@test.com",
        username="Admin",
        password_hash="hashed_password",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_package(db_session: Session):
    pkg = Package(
        slug="premium",
        name="Premium Package",
        description="Premium package for matching",
        price_cents=99900,
        currency="vnd",
        credits_match=100,
        credits_chatbot=50,
        period="30_days",
        features=["vip_listing", "priority_match"],
        active=True,
    )
    db_session.add(pkg)
    db_session.commit()
    return pkg


def test_list_packages(client, test_package):
    response = client.get("/api/v1/packages/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["slug"] == "premium"


def test_create_purchase_unauthorized(client, test_package):
    response = client.post(
        "/api/v1/packages/purchase", json={"package_id": test_package.id}
    )
    assert response.status_code == 401


def test_get_purchases_unauthorized(client):
    response = client.get("/api/v1/packages/me/purchases")
    assert response.status_code == 401


def test_get_entitlements_unauthorized(client):
    response = client.get("/api/v1/packages/me/entitlements")
    assert response.status_code == 401
