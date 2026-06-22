from pydantic import BaseModel, Field
from typing import List, Optional

class AdminPackageOut(BaseModel):
    id: str
    name: str
    icon: str
    targetCustomer: str
    targetCustomerLabel: str
    pricePerMonth: int
    duration: str
    features: List[str]
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
    
    # Custom attributes for frontend requirements
    icon: str = "file-text"
    targetCustomer: str = "owner"
    features_list: List[str] = []

class AdminPackageUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price_cents: Optional[int] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    active: Optional[bool] = None
    
    # Custom attributes for frontend requirements
    icon: Optional[str] = None
    targetCustomer: Optional[str] = None
    features_list: Optional[List[str]] = None

class AdminPackageStatusUpdate(BaseModel):
    active: bool

class AdminPackageListResponse(BaseModel):
    items: List[AdminPackageOut]
    total: int
