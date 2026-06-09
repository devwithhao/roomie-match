from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional


class PackageOut(BaseModel):
    """Package DTO for API response"""

    id: int
    slug: str
    name: str
    description: Optional[str] = None
    price_cents: int
    currency: str
    credits_match: Optional[int] = None
    credits_chatbot: Optional[int] = None
    period: Optional[str] = None
    features: Any | None = None
    active: bool

    model_config = {"from_attributes": True}


class PurchaseOut(BaseModel):
    """Purchase DTO for API response"""

    id: int
    account_id: int
    package_id: int
    provider: str
    status: str  # 'pending', 'paid', 'failed'
    amount_cents: int
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PurchaseCreate(BaseModel):
    """Request to create/initiate a purchase"""

    package_id: int = Field(..., description="Package ID to purchase")


class EntitlementOut(BaseModel):
    """Entitlement DTO for API response"""

    id: int
    account_id: int
    feature_key: str
    quantity: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
