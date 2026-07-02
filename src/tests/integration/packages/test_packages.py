import pytest
from sqlalchemy.orm import Session

from app.features.packages.models import Package
from app.features.packages.models import Entitlement
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


def test_landlord_purchase_package_is_paid_and_grants_entitlements(client, db_session: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "landlord-package@example.com",
            "password": "password123",
            "display_name": "Landlord Package",
            "account_type": "landlord",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    account_id = response.json()["user"]["id"]

    pkg = Package(
        slug="landlord-test",
        name="Landlord Test",
        description="Landlord package",
        price_cents=49000,
        currency="vnd",
        target_role="landlord",
        period="30_days",
        features={"posts_limit": 3, "photo_limit": 15, "boost_limit": 1},
        active=True,
    )
    db_session.add(pkg)
    db_session.commit()

    purchase = client.post(
        "/api/v1/packages/purchase",
        json={"package_id": pkg.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert purchase.status_code == 201
    body = purchase.json()
    assert body["status"] == "pending"
    assert body["package_id"] == pkg.id

    assert (
        db_session.query(Entitlement)
        .filter_by(account_id=account_id, source_purchase_id=body["id"])
        .count()
        == 0
    )


@pytest.mark.parametrize(
    ("slug", "price_cents", "features"),
    [
        ("landlord-basic", 49000, {"posts_limit": 3, "photo_limit": 15, "boost_limit": 0}),
        ("landlord-pro", 199000, {"posts_limit": 30, "photo_limit": 60, "boost_limit": 5}),
        ("landlord-vip", 499000, {"posts_limit": 100, "photo_limit": 150, "boost_limit": 20}),
    ],
)
def test_landlord_standard_packages_grant_expected_entitlements(
    client,
    db_session: Session,
    slug: str,
    price_cents: int,
    features: dict[str, int],
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{slug}@example.com",
            "password": "password123",
            "display_name": slug,
            "account_type": "landlord",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    account_id = response.json()["user"]["id"]

    pkg = Package(
        slug=slug,
        name=slug.replace("-", " ").title(),
        description="Standard landlord package",
        price_cents=price_cents,
        currency="vnd",
        target_role="landlord",
        period="30_days",
        features=features,
        active=True,
    )
    db_session.add(pkg)
    db_session.commit()

    purchase = client.post(
        "/api/v1/packages/purchase",
        json={"package_id": pkg.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert purchase.status_code == 201
    assert purchase.json()["amount_cents"] == price_cents
    assert purchase.json()["status"] == "pending"
    assert (
        db_session.query(Entitlement)
        .filter_by(account_id=account_id, source_purchase_id=purchase.json()["id"])
        .count()
        == 0
    )


def test_payment_confirmation_is_idempotent(client, db_session: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "idempotent-payment@example.com", "password": "password123", "display_name": "Payment", "account_type": "landlord"},
    )
    token = response.json()["access_token"]
    account_id = response.json()["user"]["id"]
    package = Package(slug="idempotent", name="Idempotent", price_cents=1000, currency="vnd", target_role="landlord", period="30_days", features={"posts_limit": 2, "photo_limit": 3, "boost_limit": 1}, active=True)
    db_session.add(package)
    db_session.commit()
    created = client.post("/api/v1/packages/purchase", json={"package_id": package.id}, headers={"Authorization": f"Bearer {token}"})
    purchase_id = created.json()["id"]

    from app.features.packages.service import PackageService
    service = PackageService(db_session)
    service.confirm_purchase(purchase_id, "txn-idempotent", {"verified": True})
    db_session.commit()
    first_count = db_session.query(Entitlement).filter_by(account_id=account_id, source_purchase_id=purchase_id).count()
    service.confirm_purchase(purchase_id, "txn-idempotent", {"verified": True})
    db_session.commit()
    assert db_session.query(Entitlement).filter_by(account_id=account_id, source_purchase_id=purchase_id).count() == first_count


def test_payment_confirmation_grants_dynamic_package_feature_quotas(client, db_session: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dynamic-package@example.com",
            "password": "password123",
            "display_name": "Dynamic Package",
            "account_type": "landlord",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    account_id = response.json()["user"]["id"]
    package = Package(
        slug="dynamic-landlord-package",
        name="Dynamic Landlord Package",
        price_cents=120000,
        currency="vnd",
        target_role="landlord",
        period="30_days",
        features={
            "posts_limit": 5,
            "featured_badge_limit": 2,
            "list": ["5 bai dang / thang", "2 huy hieu noi bat"],
            "boost_duration_days": 7,
        },
        active=True,
    )
    db_session.add(package)
    db_session.commit()

    created = client.post(
        "/api/v1/packages/purchase",
        json={"package_id": package.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    purchase_id = created.json()["id"]

    from app.features.packages.service import PackageService

    PackageService(db_session).confirm_purchase(purchase_id, "txn-dynamic", {"verified": True})
    db_session.commit()

    entitlements = {
        item.feature_key: item.quantity
        for item in db_session.query(Entitlement)
        .filter_by(account_id=account_id, source_purchase_id=purchase_id)
        .all()
    }
    assert entitlements["posts_limit"] == 5
    assert entitlements["featured_badge_limit"] == 2
    assert "list" not in entitlements
    assert "boost_duration_days" not in entitlements
    assert entitlements["active_subscription"] is None
