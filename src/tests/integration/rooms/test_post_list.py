from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.rooms.amenity import Amenity
from app.models.rooms.post import Post
from app.models.rooms.room import Room
from app.models.rooms.room_amenity import RoomAmenity
from app.models.rooms.room_image import RoomImage
from app.models.users.account import Account
from app.models.users.role import Role


def _make_landlord(db: Session) -> Account:
    role = db.query(Role).filter_by(name="landlord").first()
    acc = Account(
        email="landlord@test.com",
        username="LandlordA",
        password_hash="hashed",
        role_id=role.id,
        avatar_url="https://img.example.com/avatar.jpg",
    )
    db.add(acc)
    db.flush()
    return acc


def _make_room(db: Session, account_id: int, **overrides) -> Room:
    defaults = dict(
        account_id=account_id,
        title="Phong dep quan 1",
        room_type="phong_tro",
        area=25.0,
        price=5_000_000,
        district="Quan 1",
        ward="Phuong Ben Nghe",
        city="Ho Chi Minh",
        contact_phone="0909000111",
        contact_social="zalo:0909000111",
        bedroom_count=1,
    )
    defaults.update(overrides)
    room = Room(**defaults)
    db.add(room)
    db.flush()
    return room


def _make_post(db: Session, room_id: int, account_id: int, **overrides) -> Post:
    defaults = dict(
        room_id=room_id,
        account_id=account_id,
        status="active",
        is_vip=False,
    )
    defaults.update(overrides)
    post = Post(**defaults)
    db.add(post)
    db.flush()
    return post


class TestListPosts:
    def test_empty_list(self, client):
        r = client.get("/api/v1/posts")
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["total_pages"] == 0

    def test_only_active_posts(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)
        _make_post(db_session, room.id, landlord.id, status="active")
        _make_post(db_session, room.id, landlord.id, status="pending")
        _make_post(db_session, room.id, landlord.id, status="expired")
        db_session.commit()

        r = client.get("/api/v1/posts")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["status"] == "active"

    def test_pagination(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        for i in range(5):
            room = _make_room(db_session, landlord.id, title=f"Room {i}")
            _make_post(db_session, room.id, landlord.id)
        db_session.commit()

        r = client.get("/api/v1/posts?page=1&page_size=2")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["total_pages"] == 3

        r2 = client.get("/api/v1/posts?page=3&page_size=2")
        body2 = r2.json()
        assert len(body2["items"]) == 1

    def test_card_fields(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)
        _make_post(db_session, room.id, landlord.id)
        db_session.commit()

        r = client.get("/api/v1/posts")
        item = r.json()["items"][0]
        assert "post_id" in item
        assert "room_id" in item
        assert "title" in item
        assert "price" in item
        assert "room_type" in item
        assert "district" in item
        assert "ward" in item
        assert "created_at" in item
        assert "is_vip" in item
        assert "status" in item
        assert "bedroom_count" in item
        assert "thumbnail" in item

    def test_thumbnail_from_first_image(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)
        db_session.add_all([
            RoomImage(room_id=room.id, image_url="https://img.example.com/1.jpg"),
            RoomImage(room_id=room.id, image_url="https://img.example.com/2.jpg"),
        ])
        _make_post(db_session, room.id, landlord.id)
        db_session.commit()

        r = client.get("/api/v1/posts")
        item = r.json()["items"][0]
        assert item["thumbnail"] == "https://img.example.com/1.jpg"


class TestPostDetail:
    def test_not_found(self, client):
        r = client.get("/api/v1/posts/999")
        assert r.status_code == 404

    def test_inactive_post_returns_404(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)
        post = _make_post(db_session, room.id, landlord.id, status="pending")
        db_session.commit()

        r = client.get(f"/api/v1/posts/{post.id}")
        assert r.status_code == 404

    def test_detail_structure(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)
        post = _make_post(db_session, room.id, landlord.id)
        db_session.commit()

        r = client.get(f"/api/v1/posts/{post.id}")
        assert r.status_code == 200
        body = r.json()

        assert body["post_id"] == post.id
        assert body["status"] == "active"
        assert "created_at" in body
        assert "is_vip" in body

        assert body["room"]["room_id"] == room.id
        assert body["room"]["title"] == "Phong dep quan 1"
        assert body["room"]["price"] == 5_000_000

        assert body["landlord"]["account_id"] == landlord.id
        assert body["landlord"]["display_name"] == "LandlordA"
        assert body["landlord"]["avatar_url"] == "https://img.example.com/avatar.jpg"
        assert body["landlord"]["contact_phone"] == "0909000111"

        assert isinstance(body["images"], list)
        assert isinstance(body["amenities"], list)

    def test_detail_with_images_and_amenities(self, client, db_session: Session):
        landlord = _make_landlord(db_session)
        room = _make_room(db_session, landlord.id)

        db_session.add_all([
            RoomImage(room_id=room.id, image_url="https://img.example.com/a.jpg"),
            RoomImage(room_id=room.id, image_url="https://img.example.com/b.jpg"),
        ])
        db_session.flush()

        wifi = Amenity(name="Wifi", category="tien_ich")
        parking = Amenity(name="Bai do xe", category="tien_ich")
        db_session.add_all([wifi, parking])
        db_session.flush()

        db_session.add_all([
            RoomAmenity(room_id=room.id, amenity_id=wifi.id),
            RoomAmenity(room_id=room.id, amenity_id=parking.id),
        ])

        post = _make_post(db_session, room.id, landlord.id)
        db_session.commit()

        r = client.get(f"/api/v1/posts/{post.id}")
        assert r.status_code == 200
        body = r.json()

        assert len(body["images"]) == 2
        urls = {img["image_url"] for img in body["images"]}
        assert "https://img.example.com/a.jpg" in urls
        assert "https://img.example.com/b.jpg" in urls

        assert len(body["amenities"]) == 2
        names = {a["name"] for a in body["amenities"]}
        assert "Wifi" in names
        assert "Bai do xe" in names
