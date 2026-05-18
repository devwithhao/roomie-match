from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RoomAmenity(Base):
    __tablename__ = "room_amenities"

    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", name="fk_room_amenities_room", ondelete="CASCADE"),
        primary_key=True,
    )
    amenity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("amenities.id", name="fk_room_amenities_amenity", ondelete="CASCADE"),
        primary_key=True,
    )
