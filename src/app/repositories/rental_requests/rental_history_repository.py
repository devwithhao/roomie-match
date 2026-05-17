from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.rental_requests.rental_history import RentalHistory
from app.models.rooms.post import Post
from app.models.rooms.room import Room


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
    ) -> list[tuple[RentalHistory, Room, Post]]:
        stmt = (
            select(RentalHistory, Room, Post)
            .join(Room, RentalHistory.room_id == Room.id)
            .join(Post, RentalHistory.post_id == Post.id)
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
