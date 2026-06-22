from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.features.packages.models.entitlement import Entitlement
from app.features.packages.models.usage_event import PackageUsageEvent
from app.features.rooms.models.amenity import Amenity
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.rooms.models.room_amenity import RoomAmenity
from app.features.rooms.models.room_image import RoomImage


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


def test_landlord_create_room_publishes_active_post(client, db_session: Session, monkeypatch):
    token, landlord_id = _register(
        client,
        email="owner@example.com",
        display_name="Owner",
        account_type="landlord",
    )
    db_session.add_all(
        [
            Entitlement(account_id=landlord_id, feature_key="posts_limit", quantity=1),
            Entitlement(account_id=landlord_id, feature_key="photo_limit", quantity=1),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.features.landlord.service.upload_room_image",
        lambda file_obj, filename=None: f"https://cdn.example.com/{filename}",
    )

    payload = {
        "title": "Phong tro gan DHQG",
        "room_type": "Phong tro",
        "area": 24,
        "max_people": 2,
        "bedroom_count": 1,
        "description": "Phong sach se",
        "city": "TP. Ho Chi Minh",
        "district": "Thu Duc",
        "ward": "Linh Trung",
        "street": "So 1",
        "price": 3200000,
        "deposit": 3200000,
        "status": "available",
        "contact_name": "Owner",
        "contact_phone": "0900000000",
        "amenities": ["Wifi", "May lanh"],
    }

    response = client.post(
        "/api/v1/landlord/rooms",
        headers={"Authorization": f"Bearer {token}"},
        data={"payload": __import__("json").dumps(payload), "publish": "true"},
        files=[("images", ("room.jpg", b"fake image", "image/jpeg"))],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["room_code"] == f"TRO-{body['id']:06d}"
    assert body["images"] == ["https://cdn.example.com/room.jpg"]
    assert set(body["amenities"]) == {"Wifi", "May lanh"}

    room = db_session.get(Room, body["id"])
    assert room is not None
    assert room.account_id == landlord_id
    assert room.room_code == body["room_code"]
    assert db_session.query(RoomImage).filter_by(room_id=room.id).count() == 1
    assert db_session.query(Amenity).count() == 2
    assert db_session.query(RoomAmenity).filter_by(room_id=room.id).count() == 2

    post = db_session.query(Post).filter_by(room_id=room.id).one()
    assert post.status == "pending"
    quantities = {
        item.feature_key: item.quantity
        for item in db_session.query(Entitlement).filter_by(account_id=landlord_id).all()
    }
    assert quantities["posts_limit"] == 0
    assert quantities["photo_limit"] == 0
    events = db_session.query(PackageUsageEvent).filter_by(account_id=landlord_id).all()
    assert {(event.feature_key, event.amount, event.entity_type) for event in events} == {
        ("posts_limit", 1, "post"),
        ("photo_limit", 1, "room_image"),
    }

    public_list = client.get("/api/v1/posts")
    assert public_list.status_code == 200
    assert public_list.json()["items"] == []

    detail = client.get(f"/api/v1/posts/{post.id}")
    assert detail.status_code == 404


def test_landlord_create_room_does_not_publish_by_default(client, db_session: Session):
    token, landlord_id = _register(
        client,
        email="owner-room-only@example.com",
        display_name="Room Only Owner",
        account_type="landlord",
    )

    response = client.post(
        "/api/v1/landlord/rooms",
        headers={"Authorization": f"Bearer {token}"},
        data={"payload": __import__("json").dumps({"title": "Phong chua dang bai"})},
    )

    assert response.status_code == 201
    room_id = response.json()["id"]
    assert db_session.get(Room, room_id) is not None
    assert db_session.query(Post).filter_by(room_id=room_id, account_id=landlord_id).count() == 0


def test_landlord_cannot_access_other_landlord_room(client, db_session: Session):
    token_a, owner_a = _register(
        client,
        email="owner-a@example.com",
        display_name="Owner A",
        account_type="landlord",
    )
    token_b, _owner_b = _register(
        client,
        email="owner-b@example.com",
        display_name="Owner B",
        account_type="landlord",
    )
    assert token_a

    room = Room(
        account_id=owner_a,
        room_code="TRO-OTHER",
        title="Other room",
        status="available",
    )
    db_session.add(room)
    db_session.commit()

    response = client.get(
        f"/api/v1/landlord/rooms/{room.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_landlord_room_list_searches_code(client, db_session: Session):
    token, owner_id = _register(
        client,
        email="owner-search@example.com",
        display_name="Owner Search",
        account_type="landlord",
    )
    db_session.add_all(
        [
            Room(account_id=owner_id, room_code="TRO-ABC123", title="Match", status="available"),
            Room(account_id=owner_id, room_code="TRO-ZZZ999", title="Nope", status="rented"),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/landlord/rooms?search=ABC123",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["room_code"] == "TRO-ABC123"


def test_landlord_create_room_blocks_when_photo_quota_is_not_enough(client, db_session: Session, monkeypatch):
    token, landlord_id = _register(
        client,
        email="owner-no-photo-quota@example.com",
        display_name="Owner No Photo Quota",
        account_type="landlord",
    )
    db_session.add_all(
        [
            Entitlement(account_id=landlord_id, feature_key="posts_limit", quantity=1),
            Entitlement(account_id=landlord_id, feature_key="photo_limit", quantity=0),
        ]
    )
    db_session.commit()

    called = {"upload": False}
    monkeypatch.setattr(
        "app.features.landlord.service.upload_room_image",
        lambda file_obj, filename=None: called.__setitem__("upload", True) or "unused",
    )

    payload = {"title": "No quota room", "status": "available"}
    response = client.post(
        "/api/v1/landlord/rooms",
        headers={"Authorization": f"Bearer {token}"},
        data={"payload": __import__("json").dumps(payload), "publish": "true"},
        files=[("images", ("room.jpg", b"fake image", "image/jpeg"))],
    )

    assert response.status_code == 402
    assert called["upload"] is False
    assert db_session.query(Room).filter_by(account_id=landlord_id).count() == 0


def test_landlord_upload_failure_does_not_consume_quota(client, db_session: Session, monkeypatch):
    token, landlord_id = _register(
        client,
        email="owner-upload-fail@example.com",
        display_name="Owner Upload Fail",
        account_type="landlord",
    )
    photo_entitlement = Entitlement(account_id=landlord_id, feature_key="photo_limit", quantity=1)
    post_entitlement = Entitlement(account_id=landlord_id, feature_key="posts_limit", quantity=1)
    db_session.add_all([photo_entitlement, post_entitlement])
    db_session.commit()

    def fail_upload(_file_obj, _filename=None):
        raise RuntimeError("upload failed")

    monkeypatch.setattr("app.features.landlord.service.upload_room_image", fail_upload)

    payload = {"title": "Upload fail room", "status": "available"}
    with pytest.raises(RuntimeError, match="upload failed"):
        client.post(
            "/api/v1/landlord/rooms",
            headers={"Authorization": f"Bearer {token}"},
            data={"payload": __import__("json").dumps(payload), "publish": "true"},
            files=[("images", ("room.jpg", b"fake image", "image/jpeg"))],
        )

    db_session.refresh(photo_entitlement)
    db_session.refresh(post_entitlement)
    assert photo_entitlement.quantity == 1
    assert post_entitlement.quantity == 1
    assert db_session.query(PackageUsageEvent).filter_by(account_id=landlord_id).count() == 0


def test_landlord_update_room_consumes_only_new_uploaded_images(client, db_session: Session, monkeypatch):
    token, landlord_id = _register(
        client,
        email="owner-update-photo@example.com",
        display_name="Owner Update Photo",
        account_type="landlord",
    )
    photo_entitlement = Entitlement(account_id=landlord_id, feature_key="photo_limit", quantity=2)
    db_session.add(photo_entitlement)
    room = Room(account_id=landlord_id, room_code="TRO-UP-PHOTO", title="Update photo", status="available")
    db_session.add(room)
    db_session.flush()
    db_session.add(RoomImage(room_id=room.id, image_url="/stogate/existing.jpg"))
    db_session.commit()

    monkeypatch.setattr(
        "app.features.landlord.service.upload_room_image",
        lambda file_obj, filename=None: f"/stogate/{filename}",
    )

    payload = {"title": "Update photo", "status": "available"}
    response = client.put(
        f"/api/v1/landlord/rooms/{room.id}",
        headers={"Authorization": f"Bearer {token}"},
        data={"payload": __import__("json").dumps(payload)},
        files=[("images", ("new.jpg", b"fake image", "image/jpeg"))],
    )

    assert response.status_code == 200
    db_session.refresh(photo_entitlement)
    assert photo_entitlement.quantity == 1
    assert db_session.query(RoomImage).filter_by(room_id=room.id).count() == 2
    event = db_session.query(PackageUsageEvent).filter_by(account_id=landlord_id, feature_key="photo_limit").one()
    assert event.amount == 1
