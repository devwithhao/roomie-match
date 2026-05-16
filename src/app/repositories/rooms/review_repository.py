from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.rooms.review import Review
from app.models.users.account import Account
from app.shared.pagination.paginator import PageParams


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, review_id: int) -> Review | None:
        stmt = select(Review).where(Review.id == review_id)
        return self._db.scalars(stmt).first()

    def get_by_account_and_room(self, account_id: int, room_id: int) -> Review | None:
        stmt = (
            select(Review)
            .where(Review.account_id == account_id)
            .where(Review.room_id == room_id)
        )
        return self._db.scalars(stmt).first()

    def add(self, review: Review) -> None:
        self._db.add(review)
        self._db.flush()

    def count_by_room(self, room_id: int) -> int:
        stmt = select(func.count()).select_from(Review).where(Review.room_id == room_id)
        return self._db.scalar(stmt) or 0

    def list_by_room(
        self,
        room_id: int,
        params: PageParams,
    ) -> list[tuple[Review, Account]]:
        stmt = (
            select(Review, Account)
            .join(Account, Review.account_id == Account.id)
            .where(Review.room_id == room_id)
            .order_by(Review.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        return list(self._db.execute(stmt).all())
