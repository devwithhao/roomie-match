from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.users.models.account import Account
from app.features.matching.models.preference import UserPreference
from app.features.matching.repositories.preference_repository import PreferenceRepository
from app.features.users.repositories.profile_repository import ProfileRepository
from app.features.matching.schemas.profile import (
    CreateMatchingProfileRequest,
    MatchingProfileResponse,
)
from app.features.matching.services.roommate_matcher import RoommateMatcherService

def parse_budget(budget_str: str | None) -> tuple[int | None, int | None]:
    if not budget_str:
        return None, None
    parts = budget_str.split('-')
    if len(parts) == 2:
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            pass
    elif len(parts) == 1:
        try:
            val = int(parts[0].strip())
            return val, val
        except ValueError:
            pass
    return None, None

def format_budget(budget_min: int | None, budget_max: int | None) -> str | None:
    if budget_min is not None and budget_max is not None:
        return f"{budget_min}-{budget_max}"
    elif budget_min is not None:
        return str(budget_min)
    elif budget_max is not None:
        return str(budget_max)
    return None


class MatchingProfileService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._profiles = ProfileRepository(db)
        self._preferences = PreferenceRepository(db)

    def create_or_update_matching_profile(
        self, account: Account, payload: CreateMatchingProfileRequest
    ) -> MatchingProfileResponse:
        # Update Profile (Image)
        profile = self._profiles.get_by_account_id(account.id)
        image_url = None
        if profile:
            if payload.image is not None:
                profile.avatar_url = payload.image
                self._profiles.update(profile)
            image_url = profile.avatar_url
        else:
            if payload.image is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Basic profile must be created first to set an image.",
                )

        # Update UserPreference
        pref = self._preferences.get_by_account_id(account.id)
        
        budget_min, budget_max = None, None
        if payload.budget is not None:
            budget_min, budget_max = parse_budget(payload.budget)
            
        if pref is None:
            pref = UserPreference(
                account_id=account.id,
                introduce=payload.introduce,
                habit=payload.habit,
                target_city=payload.location,
                budget_min=budget_min,
                budget_max=budget_max,
            )
        else:
            if payload.introduce is not None:
                pref.introduce = payload.introduce
            if payload.habit is not None:
                pref.habit = payload.habit
            if payload.location is not None:
                pref.target_city = payload.location
            if payload.budget is not None:
                pref.budget_min = budget_min
                pref.budget_max = budget_max

        self._preferences.update(pref)
        self._db.commit()

        # Generate suggestions
        matcher_service = RoommateMatcherService(self._db)
        matcher_service.generate_suggestions(account.id)

        return MatchingProfileResponse(
            account_id=account.id,
            email=account.email,
            phone=profile.phone if profile else None,
            facebook=profile.facebook if profile else None,
            instagram=profile.instagram if profile else None,
            twitter=profile.twitter if profile else None,
            image=image_url,
            introduce=pref.introduce,
            habit=pref.habit,
            location=pref.target_city,
            budget=format_budget(pref.budget_min, pref.budget_max),
        )

    def get_matching_profile(self, account_id: int) -> MatchingProfileResponse:
        profile = self._profiles.get_by_account_id(account_id)
        pref = self._preferences.get_by_account_id(account_id)
        
        if not pref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matching profile not found.",
            )
            
        account = self._db.get(Account, account_id)
        
        return MatchingProfileResponse(
            account_id=account_id,
            email=account.email if account else None,
            phone=profile.phone if profile else None,
            facebook=profile.facebook if profile else None,
            instagram=profile.instagram if profile else None,
            twitter=profile.twitter if profile else None,
            image=profile.avatar_url if profile else None,
            introduce=pref.introduce,
            habit=pref.habit,
            location=pref.target_city,
            budget=format_budget(pref.budget_min, pref.budget_max),
        )
