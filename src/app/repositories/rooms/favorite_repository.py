from __future__ import annotations

from sqlalchemy import select
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

    def list_saved_posts(self, account_id: int) -> list[tuple[Post, Room, object]]:
        stmt = (
            select(Post, Room, Favorite.created_at)
            .join(Favorite, Favorite.post_id == Post.id)
            .join(Room, Post.room_id == Room.id)
            .where(Favorite.account_id == account_id)
            .order_by(Favorite.created_at.desc(), Post.id.desc())
        )
        return list(self._db.execute(stmt).all())
