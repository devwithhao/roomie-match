from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RoomImage(Base):
    __tablename__ = "room_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", name="fk_room_images_room", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
