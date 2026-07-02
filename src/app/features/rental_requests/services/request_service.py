from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.landlord.models import Notification, RentalRequest
from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rental_requests.schemas.requests import RentalRequestCreate, RentalRequestDecision, RentalRequestListOut, RentalRequestOut
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role
from app.features.users.role_utils import canonical_account_type


class RentalRequestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, account: Account, post_id: int, payload: RentalRequestCreate) -> RentalRequestOut:
        self._require_role(account, "tenant")
        row = self.db.execute(
            select(Post, Room).join(Room, Post.room_id == Room.id).where(Post.id == post_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Bài đăng không còn nhận yêu cầu thuê")
        post, room = row
        if post.status != "active" or room.status != "available":
            raise HTTPException(status_code=404, detail="Bài đăng không còn nhận yêu cầu thuê")
        existing = self.db.scalar(
            select(RentalRequest).where(
                RentalRequest.account_id == account.id,
                RentalRequest.status == "pending",
            )
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Bạn đang có một yêu cầu thuê chờ xử lý. Vui lòng hủy yêu cầu hiện tại trước khi gửi yêu cầu mới.",
            )
        request = RentalRequest(
            account_id=account.id,
            landlord_id=post.account_id,
            room_id=room.id,
            post_id=post.id,
            start_date=payload.start_date,
            note=payload.note,
        )
        self.db.add(request)
        self.db.flush()
        self._notify(post.account_id, "rental_request", "Yêu cầu thuê mới", f"Có khách xác nhận muốn thuê {room.title or 'phòng của bạn'}.", "rental_request", request.id)
        self.db.commit()
        self.db.refresh(request)
        return self._out(request, room)

    def list_tenant(self, account: Account) -> RentalRequestListOut:
        self._require_role(account, "tenant")
        rows = self.db.execute(select(RentalRequest, Room).join(Room, RentalRequest.room_id == Room.id).where(RentalRequest.account_id == account.id).order_by(RentalRequest.created_at.desc())).all()
        return RentalRequestListOut(items=[self._out(req, room) for req, room in rows], total=len(rows))

    def cancel(self, account: Account, request_id: int) -> RentalRequestOut:
        request, room = self._owned_tenant_request(account, request_id)
        if request.status != "pending":
            raise HTTPException(status_code=409, detail="Chỉ có thể hủy yêu cầu đang chờ")
        request.status = "cancelled"
        request.decided_at = datetime.utcnow()
        self._notify(request.landlord_id, "rental_request", "Yêu cầu đã hủy", f"Khách đã hủy yêu cầu thuê {room.title or 'phòng'}.", "rental_request", request.id)
        self.db.commit()
        return self._out(request, room)

    def list_landlord(
        self,
        account: Account,
        request_status: str | None = None,
        search: str | None = None,
    ) -> RentalRequestListOut:
        self._require_role(account, "landlord")
        stmt = (
            select(RentalRequest, Room)
            .join(Room, RentalRequest.room_id == Room.id)
            .outerjoin(Profile, Profile.account_id == RentalRequest.account_id)
            .outerjoin(Account, Account.id == RentalRequest.account_id)
            .where(RentalRequest.landlord_id == account.id)
        )
        if request_status:
            stmt = stmt.where(RentalRequest.status == request_status)
        if search and search.strip():
            keyword = f"%{search.strip()}%"
            predicates = [
                Profile.full_name.like(keyword),
                Profile.phone.like(keyword),
                Room.title.like(keyword),
                Room.room_code.like(keyword),
                Account.email.like(keyword),
            ]
            numeric_part = "".join(character for character in search if character.isdigit())
            if numeric_part:
                numeric_value = int(numeric_part)
                predicates.extend([
                    RentalRequest.room_id == numeric_value,
                    RentalRequest.post_id == numeric_value,
                ])
            stmt = stmt.where(or_(*predicates))
        rows = self.db.execute(stmt.order_by(RentalRequest.created_at.desc())).all()
        return RentalRequestListOut(items=[self._out(req, room) for req, room in rows], total=len(rows))

    def decide(self, account: Account, request_id: int, payload: RentalRequestDecision) -> RentalRequestOut:
        self._require_role(account, "landlord")
        row = self.db.execute(
            select(RentalRequest, Room, Post)
            .join(Room, RentalRequest.room_id == Room.id)
            .join(Post, RentalRequest.post_id == Post.id)
            .where(RentalRequest.id == request_id, RentalRequest.landlord_id == account.id)
            .with_for_update()
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
        request, room, post = row
        if request.status != "pending":
            raise HTTPException(status_code=409, detail="Yêu cầu đã được xử lý")
        request.status = payload.decision
        request.decision_reason = payload.reason
        request.decided_at = datetime.utcnow()
        if payload.decision == "accepted":
            if room.status != "available":
                raise HTTPException(status_code=409, detail="Phòng đã có người thuê")
            request.accepted_room_id = room.id
            room.status = "rented"
            room.current_people = max(1, room.current_people)
            post.status = "closed"
            post.is_vip = False
            post.boosted_at = None
            post.boost_expires_at = None
            self.db.add(RentalHistory(account_id=request.account_id, room_id=room.id, post_id=post.id, start_date=request.start_date, status="active"))
            competing = self.db.scalars(select(RentalRequest).where(RentalRequest.room_id == room.id, RentalRequest.id != request.id, RentalRequest.status == "pending")).all()
            for other in competing:
                other.status = "rejected"
                other.decision_reason = "Phòng đã có người thuê"
                other.decided_at = datetime.utcnow()
                self._notify(other.account_id, "rental_request", "Yêu cầu không được chấp nhận", f"{room.title or 'Phòng'} đã có người thuê.", "rental_request", other.id)
        self._notify(request.account_id, "rental_request", "Kết quả xác nhận thuê", f"Yêu cầu thuê {room.title or 'phòng'} đã được {payload.decision}.", "rental_request", request.id)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Phòng đã được xác nhận cho khách khác") from exc
        return self._out(request, room)

    def end_rental(self, account: Account, request_id: int) -> RentalRequestOut:
        self._require_role(account, "landlord")
        row = self.db.execute(
            select(RentalRequest, Room)
            .join(Room, RentalRequest.room_id == Room.id)
            .where(RentalRequest.id == request_id, RentalRequest.landlord_id == account.id)
            .with_for_update()
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
        request, room = row
        if request.status != "accepted":
            raise HTTPException(status_code=409, detail="Chỉ có thể kết thúc lượt thuê đã được chấp nhận")

        request.status = "ended"
        request.accepted_room_id = None
        request.decided_at = datetime.utcnow()
        room.status = "available"
        room.current_people = 0

        history = self.db.scalar(
            select(RentalHistory)
            .where(
                RentalHistory.account_id == request.account_id,
                RentalHistory.room_id == room.id,
                RentalHistory.post_id == request.post_id,
                RentalHistory.status == "active",
            )
            .order_by(RentalHistory.created_at.desc(), RentalHistory.id.desc())
        )
        if history is not None:
            history.status = "ended"
            history.end_date = date.today()

        self._notify(
            request.account_id,
            "rental_request",
            "Lượt thuê đã kết thúc",
            f"Chủ trọ đã kết thúc lượt thuê {room.title or 'phòng'}.",
            "rental_request",
            request.id,
        )
        self.db.commit()
        return self._out(request, room)

    def _owned_tenant_request(self, account: Account, request_id: int):
        row = self.db.execute(select(RentalRequest, Room).join(Room, RentalRequest.room_id == Room.id).where(RentalRequest.id == request_id, RentalRequest.account_id == account.id)).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
        return row

    def _out(self, request: RentalRequest, room: Room) -> RentalRequestOut:
        profile = self.db.get(Profile, request.account_id)
        account = self.db.get(Account, request.account_id)
        return RentalRequestOut(
            id=request.id,
            account_id=request.account_id,
            tenant_name=profile.full_name if profile else (account.username or account.email),
            tenant_email=account.email if account else None,
            tenant_phone=profile.phone if profile else None,
            tenant_gender=profile.gender if profile else None,
            tenant_avatar_url=profile.avatar_url if profile else None,
            tenant_date_of_birth=profile.date_of_birth if profile else None,
            tenant_address=profile.address if profile else None,
            tenant_hometown=profile.hometown if profile else None,
            tenant_bio=profile.bio if profile else None,
            tenant_facebook=profile.facebook if profile else None,
            tenant_instagram=profile.instagram if profile else None,
            tenant_twitter=profile.twitter if profile else None,
            landlord_id=request.landlord_id,
            room_id=request.room_id,
            post_id=request.post_id,
            room_title=room.title,
            room_code=room.room_code,
            post_code=f"P{request.post_id:03d}",
            start_date=request.start_date,
            note=request.note,
            status=request.status,
            decision_reason=request.decision_reason,
            created_at=request.created_at,
        )

    def _notify(self, account_id: int, kind: str, title: str, message: str, entity_type: str, entity_id: int) -> None:
        self.db.add(Notification(account_id=account_id, type=kind, title=title, message=message, entity_type=entity_type, entity_id=entity_id))

    def _require_role(self, account: Account, expected: str) -> None:
        role = self.db.get(Role, account.role_id)
        if role is None or canonical_account_type(role.name, role.description) != expected:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{expected} permission required")
