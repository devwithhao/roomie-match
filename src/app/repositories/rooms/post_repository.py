from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.rooms.amenity import Amenity
from app.models.rooms.post import Post
from app.models.rooms.room import Room
from app.models.rooms.room_amenity import RoomAmenity
from app.models.rooms.room_image import RoomImage
from app.models.users.account import Account
from app.schemas.rooms.search import PostSearchFilter
from app.shared.pagination.paginator import PageParams


class PostRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, post_id: int) -> Post | None:
        stmt = select(Post).where(Post.id == post_id)
        return self._db.scalars(stmt).first()

    def count_search(self, filters: PostSearchFilter | None = None) -> int:
        stmt = select(func.count()).select_from(Post).where(Post.status == "active")
        
        if filters:
            stmt = stmt.join(Room, Post.room_id == Room.id)
            if filters.city:
                stmt = stmt.where(Room.city == filters.city)
            if filters.district:
                stmt = stmt.where(Room.district == filters.district)
            if filters.ward:
                stmt = stmt.where(Room.ward == filters.ward)
            if filters.room_type:
                stmt = stmt.where(Room.room_type == filters.room_type)
            if filters.min_price is not None:
                stmt = stmt.where(Room.price >= filters.min_price)
            if filters.max_price is not None:
                stmt = stmt.where(Room.price <= filters.max_price)
            if filters.amenity_ids:
                # Room must have ALL requested amenities
                subq = (
                    select(RoomAmenity.room_id)
                    .where(RoomAmenity.amenity_id.in_(filters.amenity_ids))
                    .group_by(RoomAmenity.room_id)
                    .having(func.count(RoomAmenity.amenity_id) == len(filters.amenity_ids))
                )
                stmt = stmt.where(Room.id.in_(subq))

        return self._db.scalar(stmt) or 0

    def search_active(
        self,
        params: PageParams,
        filters: PostSearchFilter | None = None,
    ) -> list[tuple[Post, Room, str | None]]:
        thumbnail_subq = (
            select(RoomImage.image_url)
            .where(RoomImage.room_id == Room.id)
            .order_by(RoomImage.id.asc())
            .limit(1)
            .correlate(Room)
            .scalar_subquery()
            .label("thumbnail")
        )

        stmt = (
            select(Post, Room, thumbnail_subq)
            .join(Room, Post.room_id == Room.id)
            .where(Post.status == "active")
        )

        if filters:
            if filters.city:
                stmt = stmt.where(Room.city == filters.city)
            if filters.district:
                stmt = stmt.where(Room.district == filters.district)
            if filters.ward:
                stmt = stmt.where(Room.ward == filters.ward)
            if filters.room_type:
                stmt = stmt.where(Room.room_type == filters.room_type)
            if filters.min_price is not None:
                stmt = stmt.where(Room.price >= filters.min_price)
            if filters.max_price is not None:
                stmt = stmt.where(Room.price <= filters.max_price)
            if filters.amenity_ids:
                subq = (
                    select(RoomAmenity.room_id)
                    .where(RoomAmenity.amenity_id.in_(filters.amenity_ids))
                    .group_by(RoomAmenity.room_id)
                    .having(func.count(RoomAmenity.amenity_id) == len(filters.amenity_ids))
                )
                stmt = stmt.where(Room.id.in_(subq))
            
            if filters.sort_by == "price_asc":
                stmt = stmt.order_by(Room.price.asc(), Post.id.desc())
            elif filters.sort_by == "price_desc":
                stmt = stmt.order_by(Room.price.desc(), Post.id.desc())
            else:
                stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc())
        else:
            stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc())

        stmt = stmt.offset(params.offset).limit(params.limit)
        
        return list(self._db.execute(stmt).all())

    def get_active_detail(self, post_id: int) -> tuple[Post, Room, Account] | None:
        """Return (Post, Room, Account) for an active post, or None."""
        stmt = (
            select(Post, Room, Account)
            .join(Room, Post.room_id == Room.id)
            .join(Account, Post.account_id == Account.id)
            .where(Post.id == post_id)
            .where(Post.status == "active")
        )
        row = self._db.execute(stmt).first()
        if row is None:
            return None
        return row._tuple()

    def get_room_images(self, room_id: int) -> list[RoomImage]:
        stmt = (
            select(RoomImage)
            .where(RoomImage.room_id == room_id)
            .order_by(RoomImage.id.asc())
        )
        return list(self._db.scalars(stmt).all())

    def get_room_amenities(self, room_id: int) -> list[Amenity]:
        stmt = (
            select(Amenity)
            .join(RoomAmenity, RoomAmenity.amenity_id == Amenity.id)
            .where(RoomAmenity.room_id == room_id)
            .order_by(Amenity.id.asc())
        )
        return list(self._db.scalars(stmt).all())
