from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.rooms.repositories.post_repository import PostRepository
from app.features.rooms.schemas.post import (
    AmenityOut,
    ImageOut,
    LandlordOut,
    PaginatedPostListOut,
    PostCardOut,
    PostDetailOut,
    RoomDetailOut,
)
from app.features.rooms.schemas.search import PostSearchFilter
from app.features.users.models.profile import Profile
from app.shared.pagination.paginator import PageParams, total_pages


class PostService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._posts = PostRepository(db)

    def list_posts(self, page: int = 1, page_size: int = 20, filters: PostSearchFilter | None = None) -> PaginatedPostListOut:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        total = self._posts.count_search(filters)
        all_rows = self._posts.search_active(PageParams(page=1, page_size=max(total, 1)), filters)
        ranked_rows = self._rank_featured_posts(all_rows)
        offset = (page - 1) * page_size
        rows = ranked_rows[offset:offset + page_size]

        items: list[PostCardOut] = []
        for post, room, thumbnail in rows:
            items.append(
                PostCardOut(
                    post_id=post.id,
                    room_id=room.id,
                    room_code=room.room_code,
                    title=post.title or room.title,
                    description=post.description if post.description is not None else room.description,
                    thumbnail=thumbnail,
                    price=room.price,
                    room_type=room.room_type,
                    area=room.area,
                    district=room.district,
                    ward=room.ward,
                    created_at=post.created_at,
                    is_vip=self._is_boost_active(post),
                    boosted_at=post.boosted_at,
                    boost_expires_at=post.boost_expires_at,
                    boost_days_left=self._boost_days_left(post),
                    status=post.status,
                    bedroom_count=room.bedroom_count,
                )
            )

        return PaginatedPostListOut(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get_post_detail(self, post_id: int) -> PostDetailOut:
        detail = self._posts.get_active_detail(post_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or not active",
            )
        post, room, account = detail

        images = [
            ImageOut(id=img.id, image_url=img.image_url)
            for img in self._posts.get_room_images(room.id)
        ]

        amenities = [
            AmenityOut(id=a.id, name=a.name, category=a.category)
            for a in self._posts.get_room_amenities(room.id)
        ]

        profile = self._db.get(Profile, account.id)
        landlord = LandlordOut(
            account_id=account.id,
            display_name=account.username,
            avatar_url=profile.avatar_url if profile is not None else None,
            contact_phone=room.contact_phone,
            contact_social=room.contact_social,
        )

        return PostDetailOut(
            post_id=post.id,
            title=post.title or room.title,
            description=post.description if post.description is not None else room.description,
            created_at=post.created_at,
            is_vip=self._is_boost_active(post),
            boosted_at=post.boosted_at,
            boost_expires_at=post.boost_expires_at,
            boost_days_left=self._boost_days_left(post),
            status=post.status,
            room=RoomDetailOut(
                room_id=room.id,
                room_code=room.room_code,
                title=room.title,
                description=room.description,
                price=room.price,
                deposit=room.deposit,
                area=room.area,
                max_people=room.max_people,
                current_people=room.current_people,
                room_type=room.room_type,
                city=room.city,
                district=room.district,
                ward=room.ward,
                street=room.street,
                full_address=room.full_address,
                latitude=room.latitude,
                longitude=room.longitude,
                electricity_price=room.electricity_price,
                water_price=room.water_price,
                internet_price=room.internet_price,
                parking_price=room.parking_price,
            ),
            images=images,
            amenities=amenities,
            landlord=landlord,
        )

    @staticmethod
    def _naive_utc(value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    @classmethod
    def _is_boost_active(cls, post, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        expires_at = cls._naive_utc(post.boost_expires_at)
        return bool(post.is_vip and expires_at is not None and expires_at > now)

    @classmethod
    def _boost_days_left(cls, post, now: datetime | None = None) -> int:
        now = now or datetime.utcnow()
        if not cls._is_boost_active(post, now):
            return 0
        expires_at = cls._naive_utc(post.boost_expires_at)
        return max(0, math.ceil((expires_at - now).total_seconds() / 86400))

    @classmethod
    def _rank_featured_posts(cls, rows, now: datetime | None = None):
        now = now or datetime.utcnow()
        featured_by_owner = defaultdict(list)
        regular = []

        for row in rows:
            post = row[0]
            if cls._is_boost_active(post, now):
                featured_by_owner[post.account_id].append(row)
            else:
                regular.append(row)

        if not featured_by_owner:
            return regular

        for owner_rows in featured_by_owner.values():
            owner_rows.sort(
                key=lambda row: (cls._naive_utc(row[0].boosted_at) or datetime.min, row[0].id),
                reverse=True,
            )

        owner_ids = sorted(featured_by_owner)
        hour_bucket = int((now - datetime(1970, 1, 1)).total_seconds() // 3600)
        start = hour_bucket % len(owner_ids)
        owner_ids = owner_ids[start:] + owner_ids[:start]

        featured = []
        max_owner_posts = max(len(items) for items in featured_by_owner.values())
        for index in range(max_owner_posts):
            for owner_id in owner_ids:
                owner_rows = featured_by_owner[owner_id]
                if index < len(owner_rows):
                    featured.append(owner_rows[index])

        return featured + regular
