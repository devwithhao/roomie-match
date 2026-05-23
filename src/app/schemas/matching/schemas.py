from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RoomMatchRequest(BaseModel):
    budget: Optional[int] = None
    city: Optional[str] = None
    district: Optional[str] = None
    # For matching wifi/parking from request body instead of preference table
    require_wifi: Optional[bool] = False
    require_parking: Optional[bool] = False

class RoomMatchResult(BaseModel):
    room_id: int
    title: Optional[str] = None
    price: Optional[int] = None
    city: Optional[str] = None
    district: Optional[str] = None
    score: float
    matched_criteria: List[str]

class RoomMatchResponse(BaseModel):
    results: List[RoomMatchResult]

class RoommateMatchRequest(BaseModel):
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    habit: Optional[List[str]] = None
    introduce: Optional[str] = None

class RoommateMatchResult(BaseModel):
    account_id: int
    full_name: str
    avatar_url: Optional[str] = None
    score: float
    matched_criteria: List[str]

class RoommateMatchResponse(BaseModel):
    results: List[RoommateMatchResult]
