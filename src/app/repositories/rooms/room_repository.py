from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rooms.room import Room


class RoomRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, room_id: int) -> Room | None:
        stmt = select(Room).where(Room.id == room_id)
        return self._db.scalars(stmt).first()
