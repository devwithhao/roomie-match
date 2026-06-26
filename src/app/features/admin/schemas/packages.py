from pydantic import BaseModel, Field
from typing import List, Optional


class AdminPackageOut(BaseModel):
    id: str
    name: str
    icon: str
    target_role: str
    pricePerMonth: int
    duration: str
    features: List[str]
    # Entitlement quotas (hiển thị thêm thông tin)
    credits_match: int
    credits_chatbot: int
    posts_limit: int
    photo_limit: int
    boost_limit: int
    totalPurchased: int
    status: str
    statusLabel: str


class AdminPackageCreate(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    price_cents: int
    currency: str = "vnd"
    period: Optional[str] = "30_days"
    active: bool = True
    target_role: str = Field("tenant", pattern="^(tenant|landlord|all)$")
    icon: str = "file-text"

    # Tenant credits (dùng khi target_role=tenant)
    credits_match: int = 0
    credits_chatbot: int = 0

    # Landlord quotas (dùng khi target_role=landlord)
    posts_limit: int = 0
    photo_limit: int = 0
    boost_limit: int = 0

    # UI display features list
    features_list: List[str] = []


class AdminPackageUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price_cents: Optional[int] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    active: Optional[bool] = None
    target_role: Optional[str] = Field(None, pattern="^(tenant|landlord|all)$")
    icon: Optional[str] = None

    # Tenant credits
    credits_match: Optional[int] = None
    credits_chatbot: Optional[int] = None

    # Landlord quotas
    posts_limit: Optional[int] = None
    photo_limit: Optional[int] = None
    boost_limit: Optional[int] = None

    # UI display features list
    features_list: Optional[List[str]] = None


class AdminPackageStatusUpdate(BaseModel):
    active: bool


class AdminPackageListResponse(BaseModel):
    items: List[AdminPackageOut]
    total: int
