from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RoleFeatureBase(BaseModel):
    target_role: str = Field(..., max_length=20)
    feature_key: str = Field(..., max_length=50)
    feature_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    active: bool = True

class RoleFeatureCreate(RoleFeatureBase):
    pass

class RoleFeatureUpdate(BaseModel):
    target_role: Optional[str] = Field(None, max_length=20)
    feature_key: Optional[str] = Field(None, max_length=50)
    feature_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    active: Optional[bool] = None

class RoleFeatureOut(RoleFeatureBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

class RoleFeatureListResponse(BaseModel):
    items: List[RoleFeatureOut]
    total: int
