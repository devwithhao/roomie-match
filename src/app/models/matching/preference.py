from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", name="fk_user_preferences_account"),
        primary_key=True,
    )
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    habit: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    introduce: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
