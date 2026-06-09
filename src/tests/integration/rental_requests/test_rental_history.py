from __future__ import annotations

from datetime import date

from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room


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
        current_people=1,
        bedroom_count=1,
        description="Phòng cho thuê",
        city="Hồ Chí Minh",
        district="Thủ Đức",
        ward="Linh Trung",
        street="Đường số 1",
        full_address="123 Đường số 1, Linh Trung, Thủ Đức",
        price=3500000,
        status="available",
        contact_name="Chủ nhà",
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


def test_list_my_rental_history_returns_items(client, db_session):
    tenant_token, tenant_id = _register_user(
        client,
        email="tenant_history1@example.com",
        display_name="Tenant History 1",
        account_type="tenant",
    )
    _, landlord_id = _register_user(
        client,
        email="landlord_history1@example.com",
        display_name="Landlord History 1",
        account_type="landlord",
    )

    room_id, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ gần Đại học Bách Khoa",
    )

    db_session.add(
        RentalHistory(
            account_id=tenant_id,
            room_id=room_id,
            post_id=post_id,
            start_date=date(2026, 1, 1),
            end_date=None,
            status="active",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/rental-history",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["post_id"] == post_id
    assert item["room_id"] == room_id
    assert item["title"] == "Phòng trọ gần Đại học Bách Khoa"
    assert item["can_view_post"] is True
    assert item["can_review"] is False


def test_list_my_rental_history_filters_and_pagination(client, db_session):
    tenant_token, tenant_id = _register_user(
        client,
        email="tenant_history2@example.com",
        display_name="Tenant History 2",
        account_type="tenant",
    )
    _, landlord_id = _register_user(
        client,
        email="landlord_history2@example.com",
        display_name="Landlord History 2",
        account_type="landlord",
    )

    room_id_1, post_id_1 = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Studio khu trung tâm",
    )
    room_id_2, post_id_2 = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ sinh viên",
    )

    db_session.add_all(
        [
            RentalHistory(
                account_id=tenant_id,
                room_id=room_id_1,
                post_id=post_id_1,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 2, 1),
                status="completed",
            ),
            RentalHistory(
                account_id=tenant_id,
                room_id=room_id_2,
                post_id=post_id_2,
                start_date=date(2026, 3, 1),
                end_date=None,
                status="active",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/rental-history?status=completed&q=Studio&limit=1&offset=0",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["post_id"] == post_id_1
    assert item["can_review"] is True


def test_list_my_rental_history_requires_auth(client):
    response = client.get("/api/v1/users/me/rental-history")
    assert response.status_code == 401


def test_list_my_rental_history_only_returns_current_user_data(client, db_session):
    tenant_token_1, tenant_id_1 = _register_user(
        client,
        email="tenant_history3@example.com",
        display_name="Tenant History 3",
        account_type="tenant",
    )
    _, tenant_id_2 = _register_user(
        client,
        email="tenant_history4@example.com",
        display_name="Tenant History 4",
        account_type="tenant",
    )
    _, landlord_id = _register_user(
        client,
        email="landlord_history3@example.com",
        display_name="Landlord History 3",
        account_type="landlord",
    )

    room_id, post_id = _create_room_post(
        db_session,
        owner_id=landlord_id,
        title="Phòng trọ quận 9",
    )

    db_session.add(
        RentalHistory(
            account_id=tenant_id_2,
            room_id=room_id,
            post_id=post_id,
            start_date=date(2026, 4, 1),
            end_date=None,
            status="active",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/rental-history",
        headers={"Authorization": f"Bearer {tenant_token_1}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
