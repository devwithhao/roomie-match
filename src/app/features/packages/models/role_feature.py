from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer, Text, Boolean, DateTime, func, UniqueConstraint

from app.database.base import Base


class RoleFeature(Base):
    """Available features/attributes that can be assigned to packages based on role"""

    __tablename__ = "role_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'tenant', 'landlord', etc.
    feature_key: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. 'posts_limit', 'credits_match'
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'Giới hạn bài đăng'
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("target_role", "feature_key", name="uq_role_feature_key"),
    )

    def __repr__(self) -> str:
        return f"<RoleFeature(id={self.id}, target_role={self.target_role}, feature_key={self.feature_key})>"
