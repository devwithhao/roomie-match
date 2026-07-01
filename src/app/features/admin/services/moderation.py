from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.admin.schemas.moderation import PostModerationUpdate, RoomModerationUpdate, VerificationModerationUpdate
from app.features.landlord.models import LandlordVerification, Notification, PostInteraction
from app.features.packages.models.purchase import Purchase
from app.features.rooms.models.favorite import Favorite
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile


class AdminModerationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_posts(self, status_filter: str | None = None) -> list[dict]:
        stmt = (
            select(Post, Room, Account, Profile)
            .outerjoin(Room, Post.room_id == Room.id)
            .join(Account, Post.account_id == Account.id)
            .outerjoin(Profile, Profile.account_id == Account.id)
        )
        if status_filter in {None, "", "all"}:
            stmt = stmt.where(Post.status != "closed")
        elif status_filter and status_filter not in {"approved", "featured"}:
            stmt = stmt.where(Post.status == status_filter)
        elif status_filter == "approved":
            stmt = stmt.where(Post.status == "active")
        elif status_filter == "featured":
            stmt = stmt.where(Post.status == "active", Post.is_vip.is_(True), Post.boost_expires_at > datetime.utcnow())
        rows = self.db.execute(stmt.order_by(Post.created_at.desc())).all()
        result = []
        for post, room, account, profile in rows:
            views = int(self.db.scalar(select(func.count()).select_from(PostInteraction).where(PostInteraction.post_id == post.id, PostInteraction.kind == "view")) or 0)
            likes = int(self.db.scalar(select(func.count()).select_from(Favorite).where(Favorite.post_id == post.id)) or 0)
            room_id = room.id if room else post.room_id
            room_title = room.title if room else None
            room_description = room.description if room else None
            result.append({"id": post.id, "post_id": post.id, "room_id": room_id, "title": room_title or post.title or f"Post #{post.id}", "description": post.description or room_description, "author": profile.full_name if profile else (account.username or account.email), "author_account_id": account.id, "author_username": account.username, "author_email": account.email, "created_at": post.created_at, "status": "approved" if post.status == "active" else post.status, "raw_status": post.status, "moderation_reason": post.moderation_reason, "views": views, "likes": likes, "comments": 0, "isFeatured": bool(post.is_vip and post.boost_expires_at and post.boost_expires_at > datetime.utcnow())})
        return result

    def moderate_post(self, admin: Account, post_id: int, payload: PostModerationUpdate) -> dict:
        post = self.db.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        next_status = "active" if payload.status == "approved" else payload.status
        if next_status == "rejected" and not payload.reason:
            raise HTTPException(status_code=422, detail="Cần nhập lý do từ chối")
        post.status = next_status
        post.moderation_reason = payload.reason if next_status == "rejected" else None
        if next_status != "active":
            post.is_vip = False
            post.boosted_at = None
            post.boost_expires_at = None
        self.db.add(Notification(account_id=post.account_id, type="post_moderation", title="Kết quả duyệt bài", message="Bài đăng đã được duyệt." if next_status == "active" else f"Bài đăng bị từ chối: {payload.reason or ''}", entity_type="post", entity_id=post.id))
        self.db.commit()
        return {"id": post.id, "status": "approved" if post.status == "active" else post.status, "reason": post.moderation_reason}

    def list_rooms(self, status_filter: str | None = None) -> list[dict]:
        stmt = select(Room, Account, Profile).join(Account, Room.account_id == Account.id).outerjoin(Profile, Profile.account_id == Account.id)
        if status_filter:
            stmt = stmt.where(Room.status == status_filter)
        rows = self.db.execute(stmt.order_by(Room.created_at.desc())).all()
        return [{"id": room.id, "title": room.title, "code": room.room_code, "area": room.full_address or room.city or "Chưa cập nhật", "owner": profile.full_name if profile else (account.username or account.email), "status": room.status, "statusLabel": {"available": "Trống", "rented": "Đang thuê", "archived": "Tạm ngưng"}.get(room.status, room.status), "capacity": room.max_people or 1, "roomType": room.room_type, "roomTypeLabel": room.room_type or "Phòng trọ", "totalRooms": 1} for room, account, profile in rows]

    def moderate_room(self, room_id: int, payload: RoomModerationUpdate) -> dict:
        room = self.db.get(Room, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        room.status = payload.status
        if payload.status == "archived":
            for post in self.db.scalars(select(Post).where(Post.room_id == room.id)).all():
                post.status = "closed"
        self.db.commit()
        return {"id": room.id, "status": room.status}

    def list_verifications(self, status_filter: str | None = None) -> list[dict]:
        stmt = select(LandlordVerification, Account, Profile).join(Account, LandlordVerification.account_id == Account.id).outerjoin(Profile, Profile.account_id == Account.id)
        if status_filter:
            stmt = stmt.where(LandlordVerification.status == status_filter)
        return [{"id": row.id, "account_id": row.account_id, "display_name": profile.full_name if profile else account.username, "email": account.email, "legal_name": row.legal_name, "identity_number": row.identity_number, "issued_date": row.issued_date, "issued_place": row.issued_place, "front_image_url": f"/api/v1/admin/landlord-verifications/{row.id}/images/front", "back_image_url": f"/api/v1/admin/landlord-verifications/{row.id}/images/back", "status": row.status, "rejection_reason": row.rejection_reason, "created_at": row.created_at} for row, account, profile in self.db.execute(stmt.order_by(LandlordVerification.created_at.desc())).all()]

    def verification_image_path(self, verification_id: int, side: str):
        row = self.db.get(LandlordVerification, verification_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Verification not found")
        from app.features.landlord.workflow_service import LandlordWorkflowService
        return LandlordWorkflowService.verification_image_response(row.front_image_url if side == "front" else row.back_image_url)

    def moderate_verification(self, admin: Account, verification_id: int, payload: VerificationModerationUpdate) -> dict:
        row = self.db.get(LandlordVerification, verification_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Verification not found")
        if payload.status == "rejected" and not payload.reason:
            raise HTTPException(status_code=422, detail="Cần nhập lý do từ chối")
        row.status = payload.status
        row.rejection_reason = payload.reason if payload.status == "rejected" else None
        row.reviewed_by = admin.id
        row.reviewed_at = datetime.utcnow()
        self.db.add(Notification(account_id=row.account_id, type="verification", title="Kết quả xác minh CCCD", message="Hồ sơ đã được xác minh." if row.status == "approved" else f"Hồ sơ bị từ chối: {payload.reason}", entity_type="verification", entity_id=row.id))
        self.db.commit()
        return {"id": row.id, "status": row.status, "reason": row.rejection_reason}

    def list_purchases(self) -> list[dict]:
        rows = self.db.execute(select(Purchase, Account).join(Account, Purchase.account_id == Account.id).order_by(Purchase.created_at.desc())).all()
        return [{"id": purchase.id, "accountId": purchase.account_id, "customer": account.username or account.email, "packageId": purchase.package_id, "amount": purchase.amount_cents, "currency": purchase.currency, "provider": purchase.provider, "providerPaymentId": purchase.provider_payment_id, "status": purchase.status, "createdAt": purchase.created_at} for purchase, account in rows]

    def update_purchase_status(self, purchase_id: int, next_status: str) -> dict:
        purchase = self.db.get(Purchase, purchase_id)
        if purchase is None:
            raise HTTPException(status_code=404, detail="Purchase not found")
        if purchase.status == "paid":
            raise HTTPException(status_code=409, detail="Không thể thay đổi giao dịch đã thanh toán")
        if next_status not in {"failed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Trạng thái giao dịch không hợp lệ")
        purchase.status = next_status
        self.db.commit()
        return {"id": purchase.id, "status": purchase.status}

    def delete_purchase(self, purchase_id: int) -> dict:
        purchase = self.db.get(Purchase, purchase_id)
        if purchase is None:
            raise HTTPException(status_code=404, detail="Purchase not found")
        if purchase.status not in {"failed", "cancelled"}:
            raise HTTPException(status_code=409, detail="Chỉ có thể xóa giao dịch thất bại hoặc đã hủy")
        self.db.delete(purchase)
        self.db.commit()
        return {"success": True}
