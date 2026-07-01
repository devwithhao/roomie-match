from datetime import date

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.features.landlord.models import RentalRequest
from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role


def register(client, email: str, account_type: str):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123", "display_name": email.split("@")[0], "account_type": account_type})
    assert response.status_code == 200
    return response.json()["access_token"], response.json()["user"]["id"]


def create_admin(client, db: Session) -> str:
    role = db.query(Role).filter_by(name="admin").one()
    account = Account(email="workflow-admin@example.com", username="workflow-admin", password_hash=hash_password("password123"), role_id=role.id, status="active")
    db.add(account)
    db.flush()
    db.add(Profile(account_id=account.id, full_name="Workflow Admin"))
    db.commit()
    response = client.post("/api/v1/auth/login", json={"email": account.email, "password": "password123"})
    return response.json()["access_token"]


def test_post_moderation_rental_confirmation_and_review(client, db_session: Session):
    landlord_token, landlord_id = register(client, "workflow-landlord@example.com", "landlord")
    tenant_token, tenant_id = register(client, "workflow-tenant@example.com", "tenant")
    admin_token = create_admin(client, db_session)
    landlord_profile = db_session.get(Profile, landlord_id)
    landlord_profile.phone = "0901111111"
    room = Room(account_id=landlord_id, room_code="FLOW-001", title="Phòng workflow", price=2_500_000, status="available")
    db_session.add(room)
    db_session.flush()
    post = Post(room_id=room.id, account_id=landlord_id, title=room.title, status="pending", is_vip=False)
    db_session.add(post)
    db_session.commit()

    pending_posts = client.get(
        "/api/v1/admin/posts?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pending_posts.status_code == 200
    assert pending_posts.json()[0]["author"] == "workflow-landlord"
    assert pending_posts.json()[0]["author_username"] == "workflow-landlord"
    assert pending_posts.json()[0]["author_email"] == "workflow-landlord@example.com"
    assert pending_posts.json()[0]["author_account_id"] == landlord_id

    assert client.get(f"/api/v1/posts/{post.id}").status_code == 404
    approved = client.patch(f"/api/v1/admin/posts/{post.id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "approved"})
    assert approved.status_code == 200
    assert client.get(f"/api/v1/posts/{post.id}").status_code == 200

    requested = client.post(f"/api/v1/posts/{post.id}/rental-requests", headers={"Authorization": f"Bearer {tenant_token}"}, json={"start_date": date.today().isoformat(), "note": "Tôi đã chuyển vào ở"})
    assert requested.status_code == 200
    request_id = requested.json()["id"]
    duplicate = client.post(f"/api/v1/posts/{post.id}/rental-requests", headers={"Authorization": f"Bearer {tenant_token}"}, json={"start_date": date.today().isoformat()})
    assert duplicate.status_code == 409

    accepted = client.patch(f"/api/v1/landlord/rental-requests/{request_id}", headers={"Authorization": f"Bearer {landlord_token}"}, json={"decision": "accepted"})
    assert accepted.status_code == 200
    db_session.expire_all()
    assert db_session.get(Room, room.id).status == "rented"
    assert db_session.get(Post, post.id).status == "closed"
    assert db_session.query(RentalRequest).filter_by(id=request_id).one().accepted_room_id == room.id
    assert db_session.query(RentalHistory).filter_by(account_id=tenant_id, room_id=room.id, status="active").count() == 1

    reviewed = client.post(f"/api/v1/rooms/{room.id}/reviews", headers={"Authorization": f"Bearer {tenant_token}"}, json={"rating": 5, "comment": "Phòng đúng mô tả"})
    assert reviewed.status_code == 200


def test_tenant_must_cancel_existing_pending_request_before_requesting_another_post(client, db_session: Session):
    landlord_token, landlord_id = register(client, "workflow-landlord-2@example.com", "landlord")
    tenant_token, _tenant_id = register(client, "workflow-tenant-2@example.com", "tenant")
    admin_token = create_admin(client, db_session)

    room_a = Room(account_id=landlord_id, room_code="FLOW-101", title="Phòng A", price=2_500_000, status="available")
    room_b = Room(account_id=landlord_id, room_code="FLOW-102", title="Phòng B", price=2_700_000, status="available")
    db_session.add_all([room_a, room_b])
    db_session.flush()

    post_a = Post(room_id=room_a.id, account_id=landlord_id, title=room_a.title, status="pending", is_vip=False)
    post_b = Post(room_id=room_b.id, account_id=landlord_id, title=room_b.title, status="pending", is_vip=False)
    db_session.add_all([post_a, post_b])
    db_session.commit()

    assert client.patch(f"/api/v1/admin/posts/{post_a.id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "approved"}).status_code == 200
    assert client.patch(f"/api/v1/admin/posts/{post_b.id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "approved"}).status_code == 200

    requested_a = client.post(
        f"/api/v1/posts/{post_a.id}/rental-requests",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={"start_date": date.today().isoformat(), "note": "Tôi muốn thuê phòng A"},
    )
    assert requested_a.status_code == 200
    request_a_id = requested_a.json()["id"]

    landlord_requests = client.get(
        "/api/v1/landlord/rental-requests?status=pending",
        headers={"Authorization": f"Bearer {landlord_token}"},
    )
    assert landlord_requests.status_code == 200
    assert landlord_requests.json()["total"] == 1
    assert landlord_requests.json()["items"][0]["post_id"] == post_a.id

    requested_b = client.post(
        f"/api/v1/posts/{post_b.id}/rental-requests",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={"start_date": date.today().isoformat(), "note": "Tôi muốn chuyển sang phòng B"},
    )
    assert requested_b.status_code == 409
    assert "Vui lòng hủy yêu cầu hiện tại" in requested_b.json()["detail"]

    cancelled = client.patch(
        f"/api/v1/users/me/rental-requests/{request_a_id}/cancel",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    requested_b_after_cancel = client.post(
        f"/api/v1/posts/{post_b.id}/rental-requests",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={"start_date": date.today().isoformat(), "note": "Giờ tôi chọn phòng B"},
    )
    assert requested_b_after_cancel.status_code == 200
    assert requested_b_after_cancel.json()["post_id"] == post_b.id


def test_unconfirmed_tenant_cannot_review(client, db_session: Session):
    token, _tenant_id = register(client, "unconfirmed-review@example.com", "tenant")
    _, landlord_id = register(client, "review-owner@example.com", "landlord")
    room = Room(account_id=landlord_id, title="Không được review", status="available")
    db_session.add(room)
    db_session.commit()
    response = client.post(f"/api/v1/rooms/{room.id}/reviews", headers={"Authorization": f"Bearer {token}"}, json={"rating": 5, "comment": "Không hợp lệ"})
    assert response.status_code == 403


def test_verification_images_require_owner_or_admin(client, db_session: Session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "image_storage_provider", "local")
    landlord_token, _ = register(client, "verification-owner@example.com", "landlord")
    tenant_token, _ = register(client, "verification-tenant@example.com", "tenant")
    admin_token = create_admin(client, db_session)
    submitted = client.post(
        "/api/v1/landlord/verification",
        headers={"Authorization": f"Bearer {landlord_token}"},
        data={"legal_name": "Nguyen Van A", "identity_number": "012345678901", "issued_date": "2024-01-01", "issued_place": "Cục CSQLHC"},
        files={"front_image": ("front.jpg", b"front", "image/jpeg"), "back_image": ("back.jpg", b"back", "image/jpeg")},
    )
    assert submitted.status_code == 200
    assert not submitted.json()["front_image_url"].startswith("/stogate")
    assert client.get("/api/v1/landlord/verification/images/front", headers={"Authorization": f"Bearer {tenant_token}"}).status_code == 403

    pending = client.get("/api/v1/admin/landlord-verifications", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert len(pending) == 1
    assert client.get(pending[0]["front_image_url"], headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    approved = client.patch(f"/api/v1/admin/landlord-verifications/{pending[0]['id']}", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "approved"})
    assert approved.status_code == 200
