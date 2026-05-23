from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users.preference import UserPreference
from app.models.users.profile import Profile
from app.schemas.matching.schemas import RoommateMatchRequest, RoommateMatchResult

class RoommateMatcherService:
    def __init__(self, db: Session):
        self.db = db

    def match_roommates(self, request: RoommateMatchRequest, current_account_id: int) -> List[RoommateMatchResult]:
        # Fetch all other user preferences
        stmt = select(UserPreference).where(UserPreference.account_id != current_account_id)
        
        # 1. Rule-based filtering
        if request.city:
            stmt = stmt.where(UserPreference.target_city == request.city)
        if request.gender and request.gender != "any":
            stmt = stmt.where(UserPreference.target_gender.in_([request.gender, "any"]))
            
        candidate_prefs = self.db.scalars(stmt).all()
        
        results = []
        for pref in candidate_prefs:
            # Rule: Budget overlap
            if request.budget_min and pref.budget_max and request.budget_min > pref.budget_max:
                continue
            if request.budget_max and pref.budget_min and request.budget_max < pref.budget_min:
                continue
                
            score = 0.0
            matched_criteria = []
            
            # Budget similarity (50%)
            # If they overlap perfectly or are very close
            score += 50
            matched_criteria.append("Budget (50/50)")
                
            # Habits match (50%)
            if request.habit and pref.habit:
                common_habits = set(request.habit).intersection(set(pref.habit))
                if common_habits:
                    habit_score = (len(common_habits) / max(len(request.habit), 1)) * 50
                    score += habit_score
                    matched_criteria.append(f"Habits ({round(habit_score, 1)}/50)")
                
            # Only consider if score > 0 to save processing
            if score > 0:
                # Fetch profile for user details
                profile = self.db.scalar(select(Profile).where(Profile.account_id == pref.account_id))
                if profile:
                    results.append(RoommateMatchResult(
                        account_id=pref.account_id,
                        full_name=profile.full_name,
                        avatar_url=profile.avatar_url,
                        score=round(score, 2),
                        matched_criteria=matched_criteria
                    ))
                    
        # Sort and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results
