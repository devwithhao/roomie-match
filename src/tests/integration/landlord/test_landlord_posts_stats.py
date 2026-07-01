from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.features.packages.models.entitlement import Entitlement
from app.features.packages.models.package import Package
from app.features.packages.models.purchase import Purchase
from app.features.packages.models.usage_event import PackageUsageEvent
from app.features.rooms.models.favorite import Favorite
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.rooms.models.room_image import RoomImage
from app.features.users.models.profile import Profile


def _register(client, *, email: str, display_name: str, account_type: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "display_name": display_name,
            "account_type": account_type,
        },
    )
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], body["user"]["id"]


def _room(db_session: Session, owner_id: int, *, code: str, title: str, status: str = "available") -> Room:
    room = Room(
        account_id=owner_id,
        room_code=code,
        title=title,
        price=2500000,
        status=status,
    )
    db_session.add(room)
    db_session.flush()
    return room


def test_landlord_stats_uses_owned_rooms_posts_and_favorites(client, db_session: Session):
    token, owner_id = _register(
        client,
        email="stats-owner@example.com",
        display_name="Stats Owner",
        account_type="landlord",
    )
    _other_token, other_owner_id = _register(
        client,
        email="stats-other@example.com",
        display_name="Stats Other",
        account_type="landlord",
    )
    _tenant_token, tenant_id = _register(
        client,
        email="stats-tenant@example.com",
        display_name="Stats Tenant",
        account_type="tenant",
    )

    room_a = _room(db_session, owner_id, code="TRO-STATS-A", title="Stats A", status="available")
    room_b = _room(db_session, owner_id, code="TRO-STATS-B", title="Stats B", status="rented")
    other_room = _room(db_session, other_owner_id, code="TRO-STATS-OTHER", title="Other", status="available")
    post_a = Post(room_id=room_a.id, account_id=owner_id, status="active", is_vip=False)
    post_b = Post(
        room_id=room_b.id,
        account_id=owner_id,
        status="active",
        is_vip=True,
        boosted_at=datetime.utcnow(),
        boost_expires_at=datetime.utcnow() + timedelta(days=3),
    )
    other_post = Post(room_id=other_room.id, account_id=other_owner_id, status="active", is_vip=False)
    db_session.add_all([post_a, post_b, other_post])
    db_session.flush()
    db_session.add(Favorite(account_id=tenant_id, post_id=post_a.id))
    db_session.commit()

    response = client.get("/api/v1/landlord/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total_rooms"] == 2
    assert body["total_posts"] == 2
    assert body["total_favorites"] == 1
    assert all(item["label"] != "TRO-STATS-OTHER" for item in body["postPerformance"])
    assert body["postPerformance"][0]["label"] == "TRO-STATS-A"
    assert body["postPerformance"][0]["value"] == 1


def test_landlord_posts_search_filter_and_favorite_metrics(client, db_session: Session):
    token, owner_id = _register(
        client,
        email="posts-owner@example.com",
        display_name="Posts Owner",
        account_type="landlord",
    )
    other_token, other_owner_id = _register(
        client,
        email="posts-other@example.com",
        display_name="Posts Other",
        account_type="landlord",
    )
    _tenant_token, tenant_id = _register(
        client,
        email="posts-tenant@example.com",
        display_name="Posts Tenant",
        account_type="tenant",
    )

    room_a = _room(db_session, owner_id, code="TRO-POST-A", title="Searchable Room")
    room_b = _room(db_session, owner_id, code="TRO-POST-B", title="Boosted Room")
    room_c = _room(db_session, owner_id, code="TRO-POST-C", title="Pending Room")
    other_room = _room(db_session, other_owner_id, code="TRO-POST-OTHER", title="Other Room")
    post_a = Post(room_id=room_a.id, account_id=owner_id, status="active", is_vip=False)
    post_b = Post(
        room_id=room_b.id,
        account_id=owner_id,
        status="active",
        is_vip=True,
        boosted_at=datetime.utcnow(),
        boost_expires_at=datetime.utcnow() + timedelta(days=3),
    )
    post_c = Post(room_id=room_c.id, account_id=owner_id, status="pending", is_vip=False)
    other_post = Post(room_id=other_room.id, account_id=other_owner_id, status="active", is_vip=False)
    db_session.add_all([post_a, post_b, post_c, other_post])
    db_session.flush()
    db_session.add_all(
        [
            Favorite(account_id=tenant_id, post_id=post_a.id),
            RoomImage(room_id=room_a.id, image_url="/stogate/post-a.jpg"),
        ]
    )
    db_session.commit()

    search_response = client.get(
        "/api/v1/landlord/posts?search=POST-A",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["total"] == 1
    assert search_body["items"][0]["room_code"] == "TRO-POST-A"
    assert search_body["items"][0]["likes"] == 1
    assert search_body["items"][0]["thumbnail"] == "/stogate/post-a.jpg"

    boosted_response = client.get(
        "/api/v1/landlord/posts?status=boosted",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert boosted_response.status_code == 200
    assert boosted_response.json()["items"][0]["status"] == "boosted"

    pending_response = client.get(
        "/api/v1/landlord/posts?status=pending",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pending_response.status_code == 200
    assert pending_response.json()["items"][0]["status"] == "pending"

    delete_other = client.delete(
        f"/api/v1/landlord/posts/{post_a.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert delete_other.status_code == 404


def test_landlord_create_post_uses_public_content_without_changing_room(client, db_session: Session):
    token, owner_id = _register(
        client,
        email="post-content-owner@example.com",
        display_name="Post Content Owner",
        account_type="landlord",
    )
    room = _room(
        db_session,
        owner_id,
        code="TRO-CONTENT",
        title="Internal room title",
        status="available",
    )
    room.description = "Internal room description"
    db_session.add(Entitlement(account_id=owner_id, feature_key="posts_limit", quantity=1))
    profile = db_session.get(Profile, owner_id)
    profile.phone = "0901234567"
    db_session.commit()

    response = client.post(
        "/api/v1/landlord/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "room_id": room.id,
            "title": "Public post title",
            "description": "Public post description",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Public post title"
    assert body["description"] == "Public post description"
    assert body["room_title"] == "Internal room title"
    assert body["room_description"] == "Internal room description"

    entitlement = db_session.query(Entitlement).filter_by(account_id=owner_id, feature_key="posts_limit").one()
    assert entitlement.quantity == 0
    event = db_session.query(PackageUsageEvent).filter_by(account_id=owner_id, feature_key="posts_limit").one()
    assert event.amount == 1
    assert event.entity_type == "post"

    db_session.refresh(room)
    assert room.title == "Internal room title"
    assert room.description == "Internal room description"

    public_detail = client.get(f"/api/v1/posts/{body['post_id']}")
    assert public_detail.status_code == 404
    assert db_session.get(Post, body["post_id"]).status == "pending"


def test_landlord_create_post_requires_profile_phone(client, db_session: Session):
    token, owner_id = _register(
        client,
        email="post-missing-phone@example.com",
        display_name="Missing Phone Owner",
        account_type="landlord",
    )
    room = _room(
        db_session,
        owner_id,
        code="TRO-NO-PHONE",
        title="No phone room",
        status="available",
    )
    db_session.add(Entitlement(account_id=owner_id, feature_key="posts_limit", quantity=1))
    db_session.commit()

    response = client.post(
        "/api/v1/landlord/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"room_id": room.id, "title": "Should fail"},
    )

    assert response.status_code == 422
    assert "số điện thoại" in response.json()["detail"]


@pytest.mark.parametrize(("duration_days", "slug"), [(3, "landlord-pro"), (7, "landlord-vip")])
def test_landlord_boost_post_consumes_boost_entitlement(
    client, db_session: Session, duration_days: int, slug: str
):
    token, owner_id = _register(
        client,
        email="boost-owner@example.com",
        display_name="Boost Owner",
        account_type="landlord",
    )
    room_a = _room(db_session, owner_id, code="TRO-BOOST-A", title="Boost A")
    room_b = _room(db_session, owner_id, code="TRO-BOOST-B", title="Boost B")
    post_a = Post(room_id=room_a.id, account_id=owner_id, status="active", is_vip=False)
    post_b = Post(room_id=room_b.id, account_id=owner_id, status="active", is_vip=False)
    package = Package(
        slug=f"{slug}-boost-test",
        name=slug,
        price_cents=100000,
        currency="vnd",
        target_role="landlord",
        period="30_days",
        features={"boost_limit": 1, "boost_duration_days": duration_days},
    )
    db_session.add(package)
    db_session.flush()
    purchase = Purchase(
        account_id=owner_id,
        package_id=package.id,
        provider="test",
        status="paid",
        amount_cents=package.price_cents,
        currency="vnd",
    )
    db_session.add(purchase)
    db_session.flush()
    entitlement = Entitlement(
        account_id=owner_id,
        feature_key="boost_limit",
        quantity=2,
        source_purchase_id=purchase.id,
    )
    db_session.add_all([post_a, post_b, entitlement])
    db_session.commit()

    boosted = client.patch(
        f"/api/v1/landlord/posts/{post_a.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "boosted"},
    )
    assert boosted.status_code == 200
    assert boosted.json()["status"] == "boosted"
    assert boosted.json()["boost_days_left"] == duration_days
    db_session.refresh(entitlement)
    assert entitlement.quantity == 1
    event = db_session.query(PackageUsageEvent).filter_by(account_id=owner_id, feature_key="boost_limit").one()
    assert event.amount == 1
    assert event.entity_id == post_a.id

    boosted_again = client.patch(
        f"/api/v1/landlord/posts/{post_a.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "boosted"},
    )
    assert boosted_again.status_code == 200
    assert db_session.query(PackageUsageEvent).filter_by(account_id=owner_id, feature_key="boost_limit").count() == 1

    post_a.boost_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    reboosted_after_expiry = client.patch(
        f"/api/v1/landlord/posts/{post_a.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "boosted"},
    )
    assert reboosted_after_expiry.status_code == 200
    assert reboosted_after_expiry.json()["boost_days_left"] == duration_days
    db_session.refresh(entitlement)
    assert entitlement.quantity == 0
    assert db_session.query(PackageUsageEvent).filter_by(account_id=owner_id, feature_key="boost_limit").count() == 2

    rejected = client.patch(
        f"/api/v1/landlord/posts/{post_b.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "boosted"},
    )
    assert rejected.status_code == 402
    assert rejected.json()["detail"]
