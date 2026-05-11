from __future__ import annotations

from app.models.rooms.post import Post
from app.models.rooms.room import Room


def _register_user(client, *, email: str, display_name: str, account_type: str):
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


def _create_room_post(db_session, *, owner_id: int, title: str) -> tuple[int, int]:
    room = Room(
        account_id=owner_id,
        title=title,
        room_type="Phòng trọ",
        area=20.0,
        max_people=2,
        current_people=0,
        bedroom_count=1,
        description="Phòng mẫu",
        city="Hồ Chí Minh",
        district="Quận 9",
        ward="Hiệp Phú",
        street="Lê Văn Việt",
        full_address="Quận 9, TP.HCM",
        price=3500000,
        status="available",
        contact_name="Chủ trọ",
        contact_phone="0900000000",
    )
    db_session.add(room)
    db_session.flush()

    post = Post(
        room_id=room.id,
        account_id=owner_id,
        status="active",
        is_vip=False,
    )
    db_session.add(post)
    db_session.flush()
    db_session.commit()
    return room.id, post.id


def test_save_post_then_list_saved_posts(client, db_session):
    tenant_token, _ = _register_user(
        client,
        email="tenant1@example.com",
        display_name="Tenant One",
        account_type="tenant",
    )
    landlord_token, landlord_id = _register_user(
        client,
        email="landlord1@example.com",
        display_name="Landlord One",
        account_type="landlord",
    )
    assert landlord_token

    room_id, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ quận 9",
    )

    save = client.post(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert save.status_code == 200
    body = save.json()
    assert body["created"] is True
    assert body["post_id"] == post_id

    save_again = client.post(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert save_again.status_code == 200
    assert save_again.json()["created"] is False
    assert save_again.json()["post_id"] == post_id

    saved = client.get(
        "/api/v1/posts/saved",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert saved.status_code == 200
    items = saved.json()["items"]
    assert len(items) == 1
    assert items[0]["post_id"] == post_id
    assert items[0]["room_id"] == room_id


def test_save_post_requires_auth(client):
    response = client.post("/api/v1/posts/1/save")
    assert response.status_code == 401


def test_save_post_returns_404_when_missing(client):
    tenant_token, _ = _register_user(
        client,
        email="tenant2@example.com",
        display_name="Tenant Two",
        account_type="tenant",
    )

    response = client.post(
        "/api/v1/posts/999/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 404


def test_non_tenant_cannot_save_post(client, db_session):
    landlord_token, landlord_id = _register_user(
        client,
        email="landlord2@example.com",
        display_name="Landlord Two",
        account_type="landlord",
    )
    room_id, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ quận 12",
    )
    assert room_id > 0

    save = client.post(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {landlord_token}"},
    )
    assert save.status_code == 403


def test_saved_list_is_empty_before_any_save(client):
    tenant_token, _ = _register_user(
        client,
        email="tenant3@example.com",
        display_name="Tenant Three",
        account_type="tenant",
    )

    response = client.get(
        "/api/v1/posts/saved",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_saved_list_requires_auth(client):
    response = client.get("/api/v1/posts/saved")
    assert response.status_code == 401


def test_unsave_post_then_list_is_empty(client, db_session):
    tenant_token, _ = _register_user(
        client,
        email="tenant4@example.com",
        display_name="Tenant Four",
        account_type="tenant",
    )
    _, landlord_id = _register_user(
        client,
        email="landlord4@example.com",
        display_name="Landlord Four",
        account_type="landlord",
    )

    _, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ Tân Bình",
    )

    save = client.post(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert save.status_code == 200

    unsave = client.delete(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert unsave.status_code == 200
    assert unsave.json()["deleted"] is True

    saved = client.get(
        "/api/v1/posts/saved",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert saved.status_code == 200
    assert saved.json()["items"] == []


def test_unsave_requires_auth(client):
    response = client.delete("/api/v1/posts/1/save")
    assert response.status_code == 401


def test_non_tenant_cannot_unsave(client, db_session):
    landlord_token, landlord_id = _register_user(
        client,
        email="landlord5@example.com",
        display_name="Landlord Five",
        account_type="landlord",
    )
    _, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ Bình Thạnh",
    )

    response = client.delete(
        f"/api/v1/posts/{post_id}/save",
        headers={"Authorization": f"Bearer {landlord_token}"},
    )
    assert response.status_code == 403


def test_unsave_returns_404_when_post_missing(client):
    tenant_token, _ = _register_user(
        client,
        email="tenant5@example.com",
        display_name="Tenant Five",
        account_type="tenant",
    )

    response = client.delete(
        "/api/v1/posts/999/save",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 404


def test_saved_list_supports_limit_offset(client, db_session):
    tenant_token, _ = _register_user(
        client,
        email="tenant6@example.com",
        display_name="Tenant Six",
        account_type="tenant",
    )
    _, landlord_id = _register_user(
        client,
        email="landlord6@example.com",
        display_name="Landlord Six",
        account_type="landlord",
    )

    post_ids: list[int] = []
    for idx in range(3):
        _, post_id = _create_room_post(
            db_session,
            owner_id=landlord_id,
            title=f"Phòng trọ {idx}",
        )
        post_ids.append(post_id)
        save = client.post(
            f"/api/v1/posts/{post_id}/save",
            headers={"Authorization": f"Bearer {tenant_token}"},
        )
        assert save.status_code == 200

    response = client.get(
        "/api/v1/posts/saved?limit=2&offset=1",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2

    expected_order = list(reversed(post_ids))
    assert body["items"][0]["post_id"] == expected_order[1]
    assert body["items"][1]["post_id"] == expected_order[2]


def test_saved_list_pagination_validation(client):
    tenant_token, _ = _register_user(
        client,
        email="tenant7@example.com",
        display_name="Tenant Seven",
        account_type="tenant",
    )

    response = client.get(
        "/api/v1/posts/saved?limit=0",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 422

