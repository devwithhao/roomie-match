from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.matching.profile import MatchingProfileResponse

class MatchActionRequest(BaseModel):
    target_account_id: int

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

class MatchContactSocials(BaseModel):
    facebook: str = ""
    instagram: str = ""
    twitter: str = ""

class MatchContact(BaseModel):
    email: str = ""
    phone: str = ""
    socials: MatchContactSocials = MatchContactSocials()

class RoommateMatchResult(BaseModel):
    id: str
    name: str
    area: Optional[str] = None
    joinedAt: str
    avatar: Optional[str] = None
    contact: MatchContact
    
    # Old fields retained for backward compatibility
    account_id: int
    full_name: str
    avatar_url: Optional[str] = None
    score: float
    matched_criteria: List[str]

class RoommateMatchResponse(BaseModel):
    results: List[RoommateMatchResult]

class RoommateSuggestionResponse(BaseModel):
    my_profile: MatchingProfileResponse
    matches: List[RoommateMatchResult]
    total: int = 0
    page: int = 1
    size: int = 5
    total_pages: int = 0

class RejectHistoryItem(BaseModel):
    id: str
    name: str
    area: Optional[str] = None
    joinedAt: str
    avatar: Optional[str] = None
    contact: MatchContact

    account_id: int
    full_name: str
    avatar_url: Optional[str] = None
    rejected_at: datetime

class MatchHistoryItem(BaseModel):
    id: str
    name: str
    area: Optional[str] = None
    joinedAt: str
    avatar: Optional[str] = None
    contact: MatchContact

    account_id: int
    full_name: str
    avatar_url: Optional[str] = None
    matched_at: datetime
    is_matched: bool


