from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Favorite(Base):
    __tablename__ = "favorites"

    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", name="fk_favorites_account"),
        primary_key=True,
    )
    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("posts.id", name="fk_favorites_post"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
