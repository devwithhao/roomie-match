from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.features.landlord.image_uploader import upload_room_image
from app.features.landlord.schemas import (
    LandlordPostCreate,
    LandlordPostListOut,
    LandlordPostOut,
    LandlordPostUpdate,
    LandlordRoomListOut,
    LandlordRoomOut,
    LandlordRoomPayload,
    LandlordStatsOut,
)
from app.features.rooms.models.amenity import Amenity
from app.features.rooms.models.favorite import Favorite
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.rooms.models.room_amenity import RoomAmenity
from app.features.rooms.models.room_image import RoomImage
from app.features.packages.service import PackageService
from app.features.users.models.account import Account
from app.features.landlord.models import PostInteraction, RentalRequest
from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.review import Review
from app.shared.pagination.paginator import total_pages


class LandlordService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_stats(self, account: Account, *, range_filter: str) -> LandlordStatsOut:
        rooms = list(
            self._db.scalars(
                select(Room).where(Room.account_id == account.id).order_by(Room.created_at.desc(), Room.id.desc())
            ).all()
        )
        post_rows = list(
            self._db.execute(
                select(Post, Room)
                .join(Room, Post.room_id == Room.id)
                .where(Post.account_id == account.id)
                .order_by(Post.created_at.desc(), Post.id.desc())
            ).all()
        )
        posts = [post for post, _room in post_rows]
        post_ids = [post.id for post in posts]
        favorite_counts = self._favorite_counts_by_post(post_ids)
        total_favorites = sum(favorite_counts.values())
        total_views = self._interaction_count(post_ids, "view")
        total_contacts = self._interaction_count(post_ids, "contact")
        total_reviews = int(
            self._db.scalar(
                select(func.count())
                .select_from(Review)
                .join(Room, Review.room_id == Room.id)
                .where(Room.account_id == account.id)
            )
            or 0
        )
        total_tenants = int(
            self._db.scalar(
                select(func.count())
                .select_from(RentalHistory)
                .join(Room, RentalHistory.room_id == Room.id)
                .where(Room.account_id == account.id)
            )
            or 0
        )

        room_status_counts = {"rented": 0, "available": 0, "negotiating": 0}
        for room in rooms:
            room_status_counts[room.status] = room_status_counts.get(room.status, 0) + 1

        post_performance = sorted(
            (
                {
                    "label": room.room_code or room.title or f"#{room.id}",
                    "value": favorite_counts.get(post.id, 0),
                }
                for post, room in post_rows
            ),
            key=lambda item: item["value"],
            reverse=True,
        )[:5]

        room_details = []
        post_by_room_id = {room.id: post for post, room in post_rows}
        for room in rooms[:5]:
            post = post_by_room_id.get(room.id)
            favorite_count = favorite_counts.get(post.id, 0) if post is not None else 0
            room_details.append(
                {
                    "id": room.room_code or f"TRO-{room.id:06d}",
                    "room_code": room.room_code,
                    "post": room.title,
                    "title": room.title,
                    "price": room.price or 0,
                    "views": self._interaction_count([post.id], "view") if post is not None else 0,
                    "favorite_count": favorite_count,
                    "status": room.status,
                }
            )

        post_counts = self._post_counts(posts)
        return LandlordStatsOut(
            range=range_filter,
            total_rooms=len(rooms),
            total_posts=len(posts),
            total_favorites=total_favorites,
            total_views=total_views,
            total_reviews=total_reviews,
            total_tenants=total_tenants,
            total_contacts=total_contacts,
            summary=[
                {
                    "id": "posts",
                    "label": "Tổng bài đăng",
                    "value": len(posts),
                    "change": f"{post_counts.get('approved', 0)} đang hiển thị",
                    "icon": "file",
                    "tone": "green",
                },
                {
                    "id": "rooms",
                    "label": "Tổng số phòng",
                    "value": len(rooms),
                    "change": f"{room_status_counts.get('available', 0)} trống",
                    "icon": "home",
                    "tone": "muted",
                },
                {
                    "id": "views",
                    "label": "Lượt xem",
                    "value": total_views,
                    "change": "Chưa bật tracking",
                    "icon": "eye",
                    "tone": "muted",
                },
                {
                    "id": "contacts",
                    "label": "Lượt liên hệ",
                    "value": total_contacts,
                    "change": f"{total_favorites} lượt lưu",
                    "icon": "message",
                    "tone": "orange",
                },
            ],
            weeklyInteractions=self._weekly_interactions(post_ids),
            roomStatus=[
                {"label": "Đã thuê", "value": room_status_counts.get("rented", 0), "color": "#5f9f1b"},
                {"label": "Trống", "value": room_status_counts.get("available", 0), "color": "#ef4b12"},
                {
                    "label": "Thương lượng",
                    "value": room_status_counts.get("negotiating", 0),
                    "color": "#f8d5c6",
                },
            ],
            postPerformance=post_performance,
            roomDetails=room_details,
        )

    def list_rooms(
        self,
        account: Account,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status_filter: str | None,
    ) -> LandlordRoomListOut:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        stmt = select(Room).where(Room.account_id == account.id)
        count_stmt = select(func.count()).select_from(Room).where(Room.account_id == account.id)

        predicates = []
        if status_filter:
            predicates.append(Room.status == status_filter)
        if search:
            keyword = f"%{search.strip()}%"
            predicates.append(
                or_(
                    Room.title.like(keyword),
                    Room.room_code.like(keyword),
                    Room.full_address.like(keyword),
                    Room.street.like(keyword),
                    Room.district.like(keyword),
                    Room.city.like(keyword),
                )
            )

        for predicate in predicates:
            stmt = stmt.where(predicate)
            count_stmt = count_stmt.where(predicate)

        total = self._db.scalar(count_stmt) or 0
        rows = self._db.scalars(
            stmt.order_by(Room.created_at.desc(), Room.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return LandlordRoomListOut(
            items=[self._room_out(room) for room in rows],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get_room(self, account: Account, room_id: int) -> LandlordRoomOut:
        return self._room_out(self._get_owned_room(account, room_id))

    def create_room(
        self,
        account: Account,
        payload: LandlordRoomPayload,
        image_files: Iterable[object] = (),
        *,
        publish: bool = False,
    ) -> LandlordRoomOut:
        image_files = list(image_files)
        if publish:
            self._ensure_package_credit(account, "posts_limit", 1)
        self._ensure_package_credit(account, "photo_limit", len(image_files))

        try:
            room = Room(account_id=account.id, **self._room_values(payload))
            self._db.add(room)
            self._db.flush()
            room.room_code = self._make_room_code(room.id)

            self._sync_amenities(room.id, payload.amenities)
            images = self._add_images(room.id, image_files)
            for image in images:
                self._consume_package_credit(
                    account,
                    "photo_limit",
                    1,
                    entity_type="room_image",
                    entity_id=image.id,
                    metadata={"room_id": room.id},
                )

            if publish:
                post = Post(
                    room_id=room.id,
                    account_id=account.id,
                    status="pending",
                    is_vip=False,
                    title=room.title,
                    description=room.description,
                )
                self._db.add(post)
                self._db.flush()
                self._consume_package_credit(account, "posts_limit", 1, entity_type="post", entity_id=post.id)

            self._db.commit()
            self._db.refresh(room)
            return self._room_out(room)
        except Exception:
            self._db.rollback()
            raise

    def update_room(
        self,
        account: Account,
        room_id: int,
        payload: LandlordRoomPayload,
        image_files: Iterable[object] = (),
    ) -> LandlordRoomOut:
        image_files = list(image_files)
        self._ensure_package_credit(account, "photo_limit", len(image_files))

        try:
            room = self._get_owned_room(account, room_id)
            for key, value in self._room_values(payload).items():
                setattr(room, key, value)
            if not room.room_code:
                room.room_code = self._make_room_code(room.id)

            self._sync_amenities(room.id, payload.amenities)
            images = self._add_images(room.id, image_files)
            for image in images:
                self._consume_package_credit(
                    account,
                    "photo_limit",
                    1,
                    entity_type="room_image",
                    entity_id=image.id,
                    metadata={"room_id": room.id},
                )
            self._db.commit()
            self._db.refresh(room)
            return self._room_out(room)
        except Exception:
            self._db.rollback()
            raise

    def delete_room(self, account: Account, room_id: int) -> dict[str, bool]:
        try:
            room = self._get_owned_room(account, room_id)
            has_history = self._db.scalar(select(RentalHistory.id).where(RentalHistory.room_id == room.id)) is not None
            has_review = self._db.scalar(select(Review.id).where(Review.room_id == room.id)) is not None
            if has_history or has_review:
                room.status = "archived"
                for post in self._db.scalars(select(Post).where(Post.room_id == room.id)).all():
                    post.status = "closed"
                    self._clear_boost(post)
                self._db.commit()
                return {"success": True}
            post_ids = list(
                self._db.scalars(
                    select(Post.id).where(Post.room_id == room.id, Post.account_id == account.id)
                ).all()
            )
            if post_ids:
                self._db.execute(delete(Favorite).where(Favorite.post_id.in_(post_ids)))
                self._db.execute(delete(Post).where(Post.id.in_(post_ids)))
            self._db.execute(delete(RoomAmenity).where(RoomAmenity.room_id == room.id))
            self._db.execute(delete(RoomImage).where(RoomImage.room_id == room.id))
            self._db.delete(room)
            self._db.commit()
            return {"success": True}
        except Exception:
            self._db.rollback()
            raise

    def delete_room_image(self, account: Account, room_id: int, image_id: int) -> dict[str, bool]:
        self._get_owned_room(account, room_id)
        image = self._db.scalar(select(RoomImage).where(RoomImage.id == image_id, RoomImage.room_id == room_id))
        if image is None:
            raise HTTPException(status_code=404, detail="Room image not found")
        self._db.delete(image)
        self._db.commit()
        return {"success": True}

    def list_posts(
        self,
        account: Account,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status_filter: str | None,
        boosted_only: bool,
    ) -> LandlordPostListOut:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        base = select(Post, Room).join(Room, Post.room_id == Room.id).where(Post.account_id == account.id)

        filters = []
        if boosted_only:
            filters.extend(self._status_predicates("boosted"))
        elif status_filter:
            filters.extend(self._status_predicates(status_filter))
        if search:
            keyword = f"%{search.strip()}%"
            filters.append(or_(Room.title.like(keyword), Room.room_code.like(keyword)))

        stmt = base
        count_stmt = select(func.count()).select_from(Post).join(Room, Post.room_id == Room.id).where(Post.account_id == account.id)
        for predicate in filters:
            stmt = stmt.where(predicate)
            count_stmt = count_stmt.where(predicate)

        total = self._db.scalar(count_stmt) or 0
        rows = self._db.execute(
            stmt.order_by(Post.created_at.desc(), Post.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        all_posts = self._db.scalars(select(Post).where(Post.account_id == account.id)).all()

        row_post_ids = [post.id for post, _room in rows]
        favorite_counts = self._favorite_counts_by_post(row_post_ids)

        return LandlordPostListOut(
            items=[self._post_out(post, room, favorite_counts.get(post.id, 0)) for post, room in rows],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)) if total else 0,
            counts=self._post_counts(all_posts),
            engagement=self._weekly_interactions([post.id for post in all_posts]),
        )

    def create_post(self, account: Account, payload: LandlordPostCreate) -> LandlordPostOut:
        room = self._get_owned_room(account, payload.room_id)
        existing = self._db.scalars(
            select(Post).where(Post.room_id == room.id, Post.account_id == account.id)
        ).first()
        if existing is not None:
            changed = False
            if payload.title is not None:
                existing.title = payload.title
                changed = True
            if payload.description is not None:
                existing.description = payload.description
                changed = True
            if existing.status == "rejected" and changed:
                existing.status = "pending"
                existing.moderation_reason = None
            if payload.is_vip and existing.status != "active":
                raise HTTPException(status_code=409, detail="Chỉ bài đã được duyệt mới có thể đẩy nổi bật")
            if payload.is_vip and not self._is_boost_active(existing):
                self._start_boost(account, existing)
                changed = True
            elif not payload.is_vip and existing.is_vip:
                self._clear_boost(existing)
                changed = True
            if changed:
                self._db.commit()
                self._db.refresh(existing)
            return self._post_out(existing, room)

        try:
            self._ensure_package_credit(account, "posts_limit", 1)
            post = Post(
                room_id=room.id,
                account_id=account.id,
                status="pending",
                is_vip=False,
                title=payload.title or room.title,
                description=payload.description if payload.description is not None else room.description,
            )
            self._db.add(post)
            self._db.flush()
            self._consume_package_credit(account, "posts_limit", 1, entity_type="post", entity_id=post.id)
            if payload.is_vip:
                raise HTTPException(status_code=409, detail="Bài phải được admin duyệt trước khi đẩy nổi bật")
            self._db.commit()
            self._db.refresh(post)
            return self._post_out(post, room)
        except Exception:
            self._db.rollback()
            raise

    def update_post(self, account: Account, post_id: int, payload: LandlordPostUpdate) -> LandlordPostOut:
        post, room = self._get_owned_post(account, post_id)
        try:
            if payload.status:
                if payload.status == "boosted":
                    if post.status != "active":
                        raise HTTPException(status_code=409, detail="Chỉ bài đã được duyệt mới có thể đẩy nổi bật")
                    if not self._is_boost_active(post):
                        self._start_boost(account, post)
                    post.status = "active"
                elif payload.status == "approved":
                    if post.status != "active":
                        raise HTTPException(status_code=403, detail="Chủ trọ không thể tự duyệt bài")
                    self._clear_boost(post)
                else:
                    raise HTTPException(status_code=422, detail="Trạng thái bài đăng không hợp lệ")
            if payload.is_vip is not None:
                if payload.is_vip:
                    if post.status != "active":
                        raise HTTPException(status_code=409, detail="Chỉ bài đã được duyệt mới có thể đẩy nổi bật")
                    if not self._is_boost_active(post):
                        self._start_boost(account, post)
                    post.status = "active"
                else:
                    self._clear_boost(post)
            if payload.title is not None:
                post.title = payload.title
            if payload.description is not None:
                post.description = payload.description
            self._db.commit()
            self._db.refresh(post)
            return self._post_out(post, room)
        except Exception:
            self._db.rollback()
            raise

    def get_post_detail(self, account: Account, post_id: int) -> dict:
        post, room = self._get_owned_post(account, post_id)
        image_rows = list(
            self._db.scalars(
                select(RoomImage).where(RoomImage.room_id == room.id).order_by(RoomImage.id.asc())
            ).all()
        )
        amenity_names = [
            amenity.name
            for amenity in self._db.scalars(
                select(Amenity)
                .join(RoomAmenity, RoomAmenity.amenity_id == Amenity.id)
                .where(RoomAmenity.room_id == room.id)
                .order_by(Amenity.id.asc())
            ).all()
        ]
        requests_rows = self._db.execute(
            select(RentalRequest)
            .where(RentalRequest.post_id == post.id)
            .order_by(RentalRequest.created_at.desc())
        ).scalars().all()
        from app.features.users.models.profile import Profile
        rental_requests_out = []
        for req in requests_rows:
            profile = self._db.get(Profile, req.account_id)
            req_account = self._db.get(Account, req.account_id)
            rental_requests_out.append({
                "id": req.id,
                "tenant_name": profile.full_name if profile else (req_account.username if req_account else "N/A"),
                "tenant_phone": profile.phone if profile else None,
                "start_date": req.start_date.isoformat() if req.start_date else None,
                "note": req.note,
                "status": req.status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            })
        status_value = self._landlord_status(post)
        favorite_count = self._favorite_counts_by_post([post.id]).get(post.id, 0)
        views = self._interaction_count([post.id], "view")
        address = room.full_address or ", ".join(
            part for part in [room.street, room.ward, room.district, room.city] if part
        )
        return {
            "id": post.id,
            "post_id": post.id,
            "room_id": room.id,
            "room_code": room.room_code,
            "title": post.title or room.title,
            "description": post.description if post.description is not None else room.description,
            "status": status_value,
            "is_vip": status_value == "boosted",
            "boosted_at": post.boosted_at,
            "boost_expires_at": post.boost_expires_at,
            "boost_days_left": self._boost_days_left(post),
            "created_at": post.created_at,
            "moderation_reason": post.moderation_reason,
            "room": {
                "id": room.id,
                "room_code": room.room_code,
                "title": room.title,
                "description": room.description,
                "room_type": room.room_type,
                "area": room.area,
                "max_people": room.max_people,
                "current_people": room.current_people,
                "price": room.price,
                "deposit": room.deposit,
                "electricity_price": room.electricity_price,
                "water_price": room.water_price,
                "internet_price": room.internet_price,
                "parking_price": room.parking_price,
                "status": room.status,
                "city": room.city,
                "district": room.district,
                "ward": room.ward,
                "street": room.street,
                "full_address": room.full_address,
                "address": address,
                "latitude": room.latitude,
                "longitude": room.longitude,
                "contact_name": room.contact_name,
                "contact_phone": room.contact_phone,
                "contact_social": room.contact_social,
            },
            "images": [{"id": img.id, "image_url": img.image_url} for img in image_rows],
            "amenities": amenity_names,
            "rental_requests": rental_requests_out,
            "views": views,
            "likes": favorite_count,
        }

    def delete_post(self, account: Account, post_id: int) -> dict[str, bool]:
        try:
            post, _room = self._get_owned_post(account, post_id)
            has_history = self._db.scalar(select(RentalHistory.id).where(RentalHistory.post_id == post.id)) is not None
            has_requests = self._db.scalar(select(RentalRequest.id).where(RentalRequest.post_id == post.id)) is not None
            if has_history or has_requests:
                post.status = "closed"
                self._clear_boost(post)
                self._db.commit()
                return {"success": True}
            self._db.execute(delete(Favorite).where(Favorite.post_id == post.id))
            self._db.delete(post)
            self._db.commit()
            return {"success": True}
        except Exception:
            self._db.rollback()
            raise

    def _get_owned_room(self, account: Account, room_id: int) -> Room:
        room = self._db.scalars(
            select(Room).where(Room.id == room_id, Room.account_id == account.id)
        ).first()
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        return room

    def _ensure_package_credit(self, account: Account, feature_key: str, amount: int) -> None:
        if amount <= 0:
            return
        if not PackageService(self._db).has_credit(account.id, feature_key, amount):
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=self._quota_message(feature_key))

    def _consume_package_credit(
        self,
        account: Account,
        feature_key: str,
        amount: int,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        metadata: dict | None = None,
    ):
        if amount <= 0:
            return None
        event = PackageService(self._db).consume_credit_with_event(
            account.id,
            feature_key,
            amount,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
        if event is None:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=self._quota_message(feature_key))
        return event

    def _consume_boost_credit(self, account: Account, post_id: int) -> int:
        packages = PackageService(self._db)
        event = self._consume_package_credit(account, "boost_limit", 1, entity_type="post", entity_id=post_id)
        return packages.boost_duration_days_for_event(event, default=3)

    def _start_boost(self, account: Account, post: Post) -> None:
        duration_days = self._consume_boost_credit(account, post.id)
        boosted_at = datetime.utcnow()
        post.is_vip = True
        post.boosted_at = boosted_at
        post.boost_expires_at = boosted_at + timedelta(days=duration_days)

    @staticmethod
    def _clear_boost(post: Post) -> None:
        post.is_vip = False
        post.boosted_at = None
        post.boost_expires_at = None

    @staticmethod
    def _is_boost_active(post: Post, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        expires_at = post.boost_expires_at
        if not post.is_vip or expires_at is None:
            return False
        if expires_at.tzinfo is not None and now.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=None)
        return expires_at > now

    def _boost_days_left(self, post: Post) -> int:
        if not self._is_boost_active(post):
            return 0
        expires_at = post.boost_expires_at
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        seconds_left = (expires_at - datetime.utcnow()).total_seconds()
        return max(0, math.ceil(seconds_left / 86400))

    def _quota_message(self, feature_key: str) -> str:
        messages = {
            "posts_limit": "Bạn đã hết lượt đăng bài trong gói hiện tại.",
            "photo_limit": "Bạn đã hết lượt upload ảnh trong gói hiện tại.",
            "boost_limit": "Bạn đã hết lượt đẩy tin nổi bật trong gói hiện tại.",
        }
        return messages.get(feature_key, "Gói hiện tại không đủ quyền lợi để thực hiện thao tác này.")

    def _get_owned_post(self, account: Account, post_id: int) -> tuple[Post, Room]:
        row = self._db.execute(
            select(Post, Room)
            .join(Room, Post.room_id == Room.id)
            .where(Post.id == post_id, Post.account_id == account.id)
        ).first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return row._tuple()

    def _room_values(self, payload: LandlordRoomPayload) -> dict:
        values = payload.model_dump(exclude={"amenities"})
        if not values.get("full_address"):
            parts = [values.get("street"), values.get("ward"), values.get("district"), values.get("city")]
            values["full_address"] = ", ".join(str(part) for part in parts if part)
        return values

    def _sync_amenities(self, room_id: int, names: list[str]) -> None:
        clean_names = []
        seen = set()
        for name in names:
            clean = name.strip()
            key = clean.lower()
            if clean and key not in seen:
                seen.add(key)
                clean_names.append(clean)

        self._db.execute(delete(RoomAmenity).where(RoomAmenity.room_id == room_id))
        for name in clean_names:
            amenity = self._db.scalars(select(Amenity).where(func.lower(Amenity.name) == name.lower())).first()
            if amenity is None:
                amenity = Amenity(name=name, category="room")
                self._db.add(amenity)
                self._db.flush()
            self._db.add(RoomAmenity(room_id=room_id, amenity_id=amenity.id))

    def _add_images(self, room_id: int, image_files: Iterable[object]) -> list[RoomImage]:
        images: list[RoomImage] = []
        for image_file in image_files:
            filename = getattr(image_file, "filename", None)
            file_obj = getattr(image_file, "file", image_file)
            if filename == "":
                continue
            image_url = upload_room_image(file_obj, filename)
            image = RoomImage(room_id=room_id, image_url=image_url)
            self._db.add(image)
            images.append(image)
        if images:
            self._db.flush()
        return images

    def _room_out(self, room: Room) -> LandlordRoomOut:
        image_rows = list(
            self._db.scalars(
                select(RoomImage).where(RoomImage.room_id == room.id).order_by(RoomImage.id.asc())
            ).all()
        )
        images = [img.image_url for img in image_rows]
        amenities = [
            amenity.name
            for amenity in self._db.scalars(
                select(Amenity)
                .join(RoomAmenity, RoomAmenity.amenity_id == Amenity.id)
                .where(RoomAmenity.room_id == room.id)
                .order_by(Amenity.id.asc())
            ).all()
        ]
        address = room.full_address or ", ".join(
            part for part in [room.street, room.ward, room.district, room.city] if part
        )
        return LandlordRoomOut(
            id=room.id,
            room_code=room.room_code,
            code=room.room_code,
            title=room.title,
            name=room.title,
            room_type=room.room_type,
            area=room.area,
            max_people=room.max_people,
            capacity=room.max_people,
            current_people=room.current_people,
            bedroom_count=room.bedroom_count,
            description=room.description,
            city=room.city,
            district=room.district,
            ward=room.ward,
            street=room.street,
            full_address=room.full_address,
            address=address,
            latitude=room.latitude,
            longitude=room.longitude,
            price=room.price,
            deposit=room.deposit,
            electricity_price=room.electricity_price,
            water_price=room.water_price,
            internet_price=room.internet_price,
            parking_price=room.parking_price,
            status=room.status,
            contact_name=room.contact_name,
            contact_phone=room.contact_phone,
            contact_social=room.contact_social,
            images=images,
            image_items=[{"id": img.id, "image_url": img.image_url} for img in image_rows],
            amenities=amenities,
            created_at=room.created_at,
        )

    def _post_out(self, post: Post, room: Room, favorite_count: int | None = None) -> LandlordPostOut:
        status_value = self._landlord_status(post)
        boost_days_left = self._boost_days_left(post)
        thumbnail = self._db.scalars(
            select(RoomImage.image_url).where(RoomImage.room_id == room.id).order_by(RoomImage.id.asc())
        ).first()
        if favorite_count is None:
            favorite_count = self._favorite_counts_by_post([post.id]).get(post.id, 0)
        return LandlordPostOut(
            id=post.id,
            post_id=post.id,
            room_id=room.id,
            room_code=room.room_code,
            code=f"P{post.id:03d}",
            title=post.title or room.title,
            description=post.description if post.description is not None else room.description,
            room_title=room.title,
            room_description=room.description,
            author=None,
            publishedAt=post.created_at.date().isoformat(),
            created_at=post.created_at,
            status=status_value,
            is_vip=status_value == "boosted",
            boosted_at=post.boosted_at,
            boost_expires_at=post.boost_expires_at,
            boost_days_left=boost_days_left,
            views=self._interaction_count([post.id], "view"),
            likes=favorite_count,
            comments=0,
            boostDaysLeft=boost_days_left,
            boostTotalDays=(post.boost_expires_at - post.boosted_at).days if status_value == "boosted" else 0,
            badges=["Trang chủ"] if status_value == "boosted" else [],
            thumbnail=thumbnail,
            moderation_reason=post.moderation_reason,
        )

    def _favorite_counts_by_post(self, post_ids: Iterable[int]) -> dict[int, int]:
        ids = list({int(post_id) for post_id in post_ids})
        if not ids:
            return {}
        rows = self._db.execute(
            select(Favorite.post_id, func.count(Favorite.account_id))
            .where(Favorite.post_id.in_(ids))
            .group_by(Favorite.post_id)
        ).all()
        return {int(post_id): int(count) for post_id, count in rows}

    def _interaction_count(self, post_ids: Iterable[int], kind: str) -> int:
        ids = list({int(post_id) for post_id in post_ids})
        if not ids:
            return 0
        return int(
            self._db.scalar(
                select(func.count()).select_from(PostInteraction).where(
                    PostInteraction.post_id.in_(ids),
                    PostInteraction.kind == kind,
                )
            )
            or 0
        )

    def _weekly_interactions(self, post_ids: Iterable[int]) -> list[dict[str, int | str]]:
        ids = list({int(post_id) for post_id in post_ids})
        today = date.today()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        likes_by_day = {day.isoformat(): 0 for day in days}
        views_by_day = {day.isoformat(): 0 for day in days}
        contacts_by_day = {day.isoformat(): 0 for day in days}

        if ids:
            start_at = datetime.combine(days[0], time.min)
            rows = self._db.execute(
                select(func.date(Favorite.created_at), func.count(Favorite.account_id))
                .where(Favorite.post_id.in_(ids), Favorite.created_at >= start_at)
                .group_by(func.date(Favorite.created_at))
            ).all()
            for day_value, count in rows:
                key = str(day_value)
                if key in likes_by_day:
                    likes_by_day[key] = int(count)
            interaction_rows = self._db.execute(
                select(func.date(PostInteraction.created_at), PostInteraction.kind, func.count(PostInteraction.id))
                .where(PostInteraction.post_id.in_(ids), PostInteraction.created_at >= start_at)
                .group_by(func.date(PostInteraction.created_at), PostInteraction.kind)
            ).all()
            for day_value, kind, count in interaction_rows:
                key = str(day_value)
                if kind == "view" and key in views_by_day:
                    views_by_day[key] = int(count)
                elif kind == "contact" and key in contacts_by_day:
                    contacts_by_day[key] = int(count)

        return [
            {
                "label": labels[day.weekday()],
                "day": labels[day.weekday()],
                "views": views_by_day[day.isoformat()],
                "contacts": contacts_by_day[day.isoformat()],
                "likes": likes_by_day[day.isoformat()],
            }
            for day in days
        ]

    def _post_counts(self, posts: Iterable[Post]) -> dict[str, int]:
        counts = {"total": 0, "pending": 0, "approved": 0, "boosted": 0, "rejected": 0}
        for post in posts:
            counts["total"] += 1
            key = self._landlord_status(post)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _status_predicates(self, status_filter: str):
        now = datetime.utcnow()
        if status_filter == "approved":
            return [
                Post.status == "active",
                or_(Post.is_vip.is_(False), Post.boost_expires_at.is_(None), Post.boost_expires_at <= now),
            ]
        if status_filter == "boosted":
            return [Post.status == "active", Post.is_vip.is_(True), Post.boost_expires_at > now]
        return [Post.status == status_filter]

    def _landlord_status(self, post: Post) -> str:
        if post.status == "active":
            return "boosted" if self._is_boost_active(post) else "approved"
        return post.status

    def _make_room_code(self, room_id: int) -> str:
        return f"TRO-{room_id:06d}"
