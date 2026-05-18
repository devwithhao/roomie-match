from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("accounts.id", name="fk_profiles_account"),
        primary_key=True,
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "other", name="gender_enum"),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
