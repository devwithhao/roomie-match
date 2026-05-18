from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.rooms.favorite import Favorite
from app.models.rooms.post import Post
from app.models.rooms.room import Room


class FavoriteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_account_and_post(self, account_id: int, post_id: int) -> Favorite | None:
        stmt = (
            select(Favorite)
            .where(Favorite.account_id == account_id)
            .where(Favorite.post_id == post_id)
        )
        return self._db.scalars(stmt).first()

    def add(self, favorite: Favorite) -> None:
        self._db.add(favorite)

    def delete_by_account_and_post(self, account_id: int, post_id: int) -> bool:
        favorite = self.get_by_account_and_post(account_id, post_id)
        if favorite is None:
            return False
        self._db.delete(favorite)
        return True

    def count_saved_posts(self, account_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Favorite)
            .where(Favorite.account_id == account_id)
        )
        return int(self._db.scalar(stmt) or 0)

    def list_saved_posts(
        self,
        account_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[tuple[Post, Room, object]]:
        stmt = (
            select(Post, Room, Favorite.created_at)
            .join(Favorite, Favorite.post_id == Post.id)
            .join(Room, Post.room_id == Room.id)
            .where(Favorite.account_id == account_id)
            .order_by(Favorite.created_at.desc(), Post.id.desc())
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._db.execute(stmt).all())
