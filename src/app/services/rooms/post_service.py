from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.rooms.post_repository import PostRepository
from app.schemas.rooms.post import (
    AmenityOut,
    ImageOut,
    LandlordOut,
    PaginatedPostListOut,
    PostCardOut,
    PostDetailOut,
    RoomDetailOut,
)
from app.shared.pagination.paginator import PageParams, total_pages


class PostService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._posts = PostRepository(db)

    def list_posts(self, page: int = 1, page_size: int = 20) -> PaginatedPostListOut:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        params = PageParams(page=page, page_size=page_size)
        total = self._posts.count_active()
        rows = self._posts.list_active(params)

        items: list[PostCardOut] = []
        for post, room, thumbnail in rows:
            items.append(
                PostCardOut(
                    post_id=post.id,
                    room_id=room.id,
                    title=room.title,
                    thumbnail=thumbnail,
                    price=room.price,
                    room_type=room.room_type,
                    area=room.area,
                    district=room.district,
                    ward=room.ward,
                    created_at=post.created_at,
                    is_vip=post.is_vip,
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

        landlord = LandlordOut(
            account_id=account.id,
            display_name=account.username,
            avatar_url=account.avatar_url,
            contact_phone=room.contact_phone,
            contact_social=room.contact_social,
        )

        return PostDetailOut(
            post_id=post.id,
            created_at=post.created_at,
            is_vip=post.is_vip,
            status=post.status,
            room=RoomDetailOut(
                room_id=room.id,
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
