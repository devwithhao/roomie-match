import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import get_db
from app.models.packages import Package, Purchase, Entitlement
from app.models.users import Account, Role

client = TestClient(app)


@pytest.fixture
def admin_user(db: Session):
    """Create an admin user for testing"""
    role = db.query(Role).filter(Role.name == "admin").first()
    if not role:
        role = Role(name="admin", description="Admin role")
        db.add(role)
        db.flush()

    user = Account(
        email="admin@test.com", hashed_password="hashed_password", role_id=role.id
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def test_package(db: Session):
    """Create a test package"""
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
    db.add(pkg)
    db.commit()
    return pkg


def test_list_packages(db: Session, test_package):
    """Test GET /packages"""
    response = client.get("/api/v1/packages/packages")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["slug"] == "premium"


def test_create_purchase_unauthorized(test_package):
    """Test POST /purchase without auth"""
    response = client.post(
        "/api/v1/packages/purchase", json={"package_id": test_package.id}
    )
    assert response.status_code == 401


def test_get_purchases_unauthorized():
    """Test GET /me/purchases without auth"""
    response = client.get("/api/v1/packages/me/purchases")
    assert response.status_code == 401


def test_get_entitlements_unauthorized():
    """Test GET /me/entitlements without auth"""
    response = client.get("/api/v1/packages/me/entitlements")
    assert response.status_code == 401
