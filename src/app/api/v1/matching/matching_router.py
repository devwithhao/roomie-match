from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
# Assuming there is a dependency for getting current user (if auth is needed)
# from app.api.dependencies.auth import get_current_user

from app.schemas.matching.schemas import (
    RoomMatchRequest,
    RoomMatchResponse,
    RoommateMatchRequest,
    RoommateMatchResponse
)
from app.services.matching.room_matcher import RoomMatcherService
from app.services.matching.roommate_matcher import RoommateMatcherService

router = APIRouter(prefix="/matching", tags=["matching"])

@router.post("/rooms", response_model=RoomMatchResponse)
def match_rooms(
    request: RoomMatchRequest,
    db: Session = Depends(get_db)
):
    """
    Find best matching rooms based on rule-based filtering and weighted scoring.
    """
    service = RoomMatcherService(db)
    results = service.match_rooms(request)
    return RoomMatchResponse(results=results)

@router.post("/roommates", response_model=RoommateMatchResponse)
def match_roommates(
    request: RoommateMatchRequest,
    db: Session = Depends(get_db)
    # current_user: Account = Depends(get_current_user)
):
    """
    Find best matching roommates based on rule-based filtering and weighted scoring.
    Currently uses account_id=0 for testing if no auth is provided.
    """
    # For MVP, we pass a dummy current_account_id if auth is not strictly required here.
    # In a real scenario, use current_user.id
    current_account_id = 0 
    
    service = RoommateMatcherService(db)
    results = service.match_roommates(request, current_account_id)
    return RoommateMatchResponse(results=results)
