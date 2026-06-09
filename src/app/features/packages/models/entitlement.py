from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer, DateTime, func, ForeignKey

from app.database.base import Base


class Entitlement(Base):
    """Entitlement: credits or features granted to accounts"""

    __tablename__ = "entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'match', 'chatbot', 'vip_listing'
    quantity: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # None = unlimited
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # None = no expiry
    source_purchase_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("purchases.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Entitlement(id={self.id}, account_id={self.account_id}, feature_key={self.feature_key}, quantity={self.quantity})>"
