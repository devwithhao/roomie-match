from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rooms.post import Post


class PostRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, post_id: int) -> Post | None:
        stmt = select(Post).where(Post.id == post_id)
        return self._db.scalars(stmt).first()
