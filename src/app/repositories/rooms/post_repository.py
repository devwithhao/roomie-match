from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.rooms.amenity import Amenity
from app.models.rooms.post import Post
from app.models.rooms.room import Room
from app.models.rooms.room_amenity import RoomAmenity
from app.models.rooms.room_image import RoomImage
from app.models.users.account import Account
from app.shared.pagination.paginator import PageParams


class PostRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, post_id: int) -> Post | None:
        stmt = select(Post).where(Post.id == post_id)
        return self._db.scalars(stmt).first()

    def count_active(self) -> int:
        stmt = select(func.count()).select_from(Post).where(Post.status == "active")
        return self._db.scalar(stmt) or 0

    def list_active(self, params: PageParams) -> list[tuple[Post, Room, str | None]]:
        """Return (Post, Room, thumbnail_url) tuples for active posts, ordered newest first."""
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
            .order_by(Post.created_at.desc(), Post.id.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
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
