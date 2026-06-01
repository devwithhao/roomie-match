from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.matching.preference import UserPreference
from app.models.matching.match import UserMatch
from app.models.matching.reject import UserReject
from app.models.users.profile import Profile
from app.models.users.account import Account
from app.schemas.matching.schemas import RoommateMatchResult, MatchContact, MatchContactSocials

class RoommateMatcherService:
    def __init__(self, db: Session):
        self.db = db

    def match_roommates(self, current_account_id: int) -> List[RoommateMatchResult]:
        # Fetch current user preference
        current_pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == current_account_id))
        
        if not current_pref:
            return [] # Returns empty if no profile

        # Exclude IDs (self, matched, rejected)
        excluded_ids = {current_account_id}
        
        # Add matched users
        matches = self.db.scalars(
            select(UserMatch).where(
                or_(UserMatch.account_id_1 == current_account_id, UserMatch.account_id_2 == current_account_id)
            )
        ).all()
        for m in matches:
            excluded_ids.add(m.account_id_1 if m.account_id_2 == current_account_id else m.account_id_2)
            
        # Add rejected users
        rejects = self.db.scalars(
            select(UserReject).where(UserReject.account_id == current_account_id)
        ).all()
        for r in rejects:
            excluded_ids.add(r.rejected_account_id)

        # Fetch candidate preferences
        stmt = select(UserPreference).where(
            UserPreference.account_id.notin_(excluded_ids)
        )
        
        # 1. Rule-based filtering
        if current_pref.target_city:
            stmt = stmt.where(UserPreference.target_city == current_pref.target_city)
        if current_pref.target_gender and current_pref.target_gender != "any":
            stmt = stmt.where(UserPreference.target_gender.in_([current_pref.target_gender, "any"]))
            
        candidate_prefs = self.db.scalars(stmt).all()
        
        results = []
        for pref in candidate_prefs:
            # Rule: Budget overlap
            if current_pref.budget_min and pref.budget_max and current_pref.budget_min > pref.budget_max:
                continue
            if current_pref.budget_max and pref.budget_min and current_pref.budget_max < pref.budget_min:
                continue
                
            score = 0.0
            matched_criteria = []
            
            # Budget similarity (50%)
            score += 50
            matched_criteria.append("Budget (50/50)")
                
            # Habits match (50%)
            if current_pref.habit and pref.habit:
                common_habits = set(current_pref.habit).intersection(set(pref.habit))
                if common_habits:
                    habit_score = (len(common_habits) / max(len(current_pref.habit), 1)) * 50
                    score += habit_score
                    matched_criteria.append(f"Habits ({round(habit_score, 1)}/50)")
                
            # Only consider if score > 0 to save processing
            if score > 0:
                # Fetch profile for user details
                profile = self.db.scalar(select(Profile).where(Profile.account_id == pref.account_id))
                account = self.db.scalar(select(Account).where(Account.id == pref.account_id))
                if profile and account:
                    contact = MatchContact(
                        email=account.email or "",
                        phone=profile.phone or "",
                        socials=MatchContactSocials()
                    )
                    joined_at = profile.created_at.strftime("%d/%m/%Y") if profile.created_at else ""
                    area_val = pref.target_district or pref.target_city or ""
                    
                    results.append(RoommateMatchResult(
                        id=f"m-{pref.account_id:02d}",
                        name=profile.full_name,
                        area=area_val,
                        joinedAt=joined_at,
                        avatar=profile.avatar_url,
                        contact=contact,
                        account_id=pref.account_id,
                        full_name=profile.full_name,
                        avatar_url=profile.avatar_url,
                        score=round(score, 2),
                        matched_criteria=matched_criteria
                    ))
                    
        # Sort and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results
