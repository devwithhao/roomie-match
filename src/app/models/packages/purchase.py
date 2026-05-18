from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer, JSON, DateTime, func, ForeignKey

from app.database.base import Base


class Purchase(Base):
    """Purchase/payment transaction record"""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packages.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'stripe', 'zalopay', etc.
    provider_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # transaction ID from provider
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="vnd", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'pending', 'paid', 'failed'
    raw_payload: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # webhook payload for debugging
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Purchase(id={self.id}, account_id={self.account_id}, package_id={self.package_id}, status={self.status})>"
