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
    # Dynamic feature quotas (hiển thị thông tin)
    feature_quotas: dict
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

    # Dynamic feature quotas
    feature_quotas: Optional[dict] = Field(default_factory=dict)

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

    # Dynamic feature quotas
    feature_quotas: Optional[dict] = None

    # UI display features list
    features_list: Optional[List[str]] = None


class AdminPackageStatusUpdate(BaseModel):
    active: bool


class AdminPackageListResponse(BaseModel):
    items: List[AdminPackageOut]
    total: int
