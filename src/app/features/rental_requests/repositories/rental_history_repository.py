from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room
from app.features.rooms.models.review import Review
from app.features.rooms.models.room_image import RoomImage


class RentalHistoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def count_by_account(
        self,
        account_id: int,
        *,
        status: str | None = None,
        query: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(RentalHistory)
            .join(Room, RentalHistory.room_id == Room.id)
            .where(RentalHistory.account_id == account_id)
        )
        if status:
            stmt = stmt.where(RentalHistory.status == status)
        if query:
            like_q = f"%{query}%"
            stmt = stmt.where(
                Room.title.ilike(like_q) | Room.full_address.ilike(like_q)
            )
        return int(self._db.scalar(stmt) or 0)

    def list_by_account(
        self,
        account_id: int,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        query: str | None = None,
    ) -> list[tuple[RentalHistory, Room, Post, Review | None, str | None]]:
        # Subquery: first image for each room
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
            select(RentalHistory, Room, Post, Review, thumbnail_subq)
            .join(Room, RentalHistory.room_id == Room.id)
            .join(Post, RentalHistory.post_id == Post.id)
            .outerjoin(
                Review,
                (Review.room_id == RentalHistory.room_id) & (Review.account_id == account_id)
            )
            .where(RentalHistory.account_id == account_id)
            .order_by(RentalHistory.start_date.desc(), RentalHistory.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(RentalHistory.status == status)
        if query:
            like_q = f"%{query}%"
            stmt = stmt.where(
                Room.title.ilike(like_q) | Room.full_address.ilike(like_q)
            )
        return list(self._db.execute(stmt).all())
