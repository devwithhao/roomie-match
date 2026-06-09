from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer, Text, JSON, Boolean, DateTime, func

from app.database.base import Base


class Package(Base):
    """Package subscription definition"""

    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="vnd", nullable=False)
    credits_match: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credits_chatbot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # '30_days', 'annual', etc.
    features: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # ['vip_listing', 'priority_match']
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Package(id={self.id}, slug={self.slug}, name={self.name})>"
