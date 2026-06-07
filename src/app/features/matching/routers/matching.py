from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
# Assuming there is a dependency for getting current user (if auth is needed)
# from app.api.dependencies.auth import get_current_user

from app.features.matching.schemas.schemas import (
    RoomMatchRequest,
    RoomMatchResponse,
    RoommateMatchRequest,
    RoommateMatchResponse,
    RoommateSuggestionResponse,
    MatchActionRequest,
)
from app.features.matching.schemas.profile import (
    CreateMatchingProfileRequest,
    MatchingProfileResponse,
)
from app.features.matching.services.room_matcher import RoomMatcherService
from app.features.matching.services.roommate_matcher import RoommateMatcherService
from app.features.matching.services.profile_service import MatchingProfileService
from app.features.matching.services.match_interaction_service import MatchInteractionService
from app.features.users.models.account import Account
from app.features.users.dependencies import get_current_account
from typing import List

router = APIRouter(prefix="/matching", tags=["matching"])

@router.post("/rooms", response_model=RoomMatchResponse)
def match_rooms(
    request: RoomMatchRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Find best matching rooms based on user preference profile.
    """
    service = RoomMatcherService(db)
    results = service.match_rooms(account.id, request)
    return RoomMatchResponse(results=results)

@router.post("/roommates", response_model=RoommateMatchResponse)
def match_roommates(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Find best matching roommates based on user preference profile.
    """
    service = RoommateMatcherService(db)
    results = service.match_roommates(account.id)
    return RoommateMatchResponse(results=results)

@router.get("/roommates/suggestions", response_model=RoommateSuggestionResponse)
def get_roommate_suggestions(
    page: int = 1,
    size: int = 5,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """
    Get the current user's matching profile and recommended roommates.
    """
    my_profile = MatchingProfileService(db).get_matching_profile(account.id)
    results, total = RoommateMatcherService(db).get_suggestions(account.id, page, size)
    
    total_pages = (total + size - 1) // size if size > 0 else 0
    
    return RoommateSuggestionResponse(
        my_profile=my_profile,
        matches=results,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.post("/profile", response_model=MatchingProfileResponse)
def create_my_matching_profile(
    payload: CreateMatchingProfileRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Create or update a matching profile for the current user.
    """
    return MatchingProfileService(db).create_or_update_matching_profile(account, payload)

@router.get("/profile", response_model=MatchingProfileResponse)
def get_my_matching_profile(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Get the current user's matching profile.
    """
    return MatchingProfileService(db).get_matching_profile(account.id)


@router.post("/roommates/accept")
def accept_roommate(
    payload: MatchActionRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    return MatchInteractionService(db).accept_user(account.id, payload.target_account_id)

@router.post("/roommates/reject")
def reject_roommate(
    payload: MatchActionRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    return MatchInteractionService(db).reject_user(account.id, payload.target_account_id)

@router.post("/roommates/unmatch")
def unmatch_roommate(
    payload: MatchActionRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    return MatchInteractionService(db).unmatch_user(account.id, payload.target_account_id)

@router.get("/roommates/rejects")
def get_reject_history(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    return MatchInteractionService(db).get_reject_history(account.id)

@router.get("/roommates/history")
def get_match_history(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    return MatchInteractionService(db).get_match_history(account.id)


