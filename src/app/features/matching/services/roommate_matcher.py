from typing import List, Tuple
import random
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.features.matching.models.preference import UserPreference
from app.features.matching.models.match import UserMatch
from app.features.matching.models.reject import UserReject
from app.features.users.models.profile import Profile
from app.features.users.models.account import Account
from app.features.matching.schemas.schemas import RoommateMatchResult, MatchContact, MatchContactSocials

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

    def generate_suggestions(self, current_account_id: int) -> list[int]:
        current_pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == current_account_id))
        if not current_pref:
            return []
            
        matches = self.match_roommates(current_account_id)
        suggested_ids = [m.account_id for m in matches[:10]]
        
        if len(suggested_ids) < 10:
            needed = 10 - len(suggested_ids)
            excluded_ids = {current_account_id}
            excluded_ids.update(suggested_ids)
            
            matched = self.db.scalars(
                select(UserMatch).where(
                    or_(UserMatch.account_id_1 == current_account_id, UserMatch.account_id_2 == current_account_id)
                )
            ).all()
            for m in matched:
                excluded_ids.add(m.account_id_1 if m.account_id_2 == current_account_id else m.account_id_2)
                
            rejects = self.db.scalars(
                select(UserReject).where(UserReject.account_id == current_account_id)
            ).all()
            for r in rejects:
                excluded_ids.add(r.rejected_account_id)
                
            available_prefs = self.db.scalars(
                select(UserPreference).where(UserPreference.account_id.notin_(excluded_ids))
            ).all()
            
            random_prefs = random.sample(available_prefs, min(needed, len(available_prefs)))
            suggested_ids.extend([p.account_id for p in random_prefs])
            
        current_pref.suggested_accounts = suggested_ids
        self.db.commit()
        return suggested_ids

    def get_suggestions(self, current_account_id: int, page: int = 1, size: int = 5) -> Tuple[List[RoommateMatchResult], int]:
        current_pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == current_account_id))
        if not current_pref:
            return [], 0
            
        suggested_ids = current_pref.suggested_accounts
        if not suggested_ids:
            suggested_ids = self.generate_suggestions(current_account_id)
            
        total = len(suggested_ids)
        start = (page - 1) * size
        end = start + size
        page_ids = suggested_ids[start:end]
        
        if not page_ids:
            return [], total
            
        results = []
        for target_id in page_ids:
            pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == target_id))
            profile = self.db.scalar(select(Profile).where(Profile.account_id == target_id))
            account = self.db.scalar(select(Account).where(Account.id == target_id))
            
            if not profile or not account or not pref:
                continue
                
            score = 0.0
            matched_criteria = []
            
            if not (current_pref.budget_min and pref.budget_max and current_pref.budget_min > pref.budget_max) and \
               not (current_pref.budget_max and pref.budget_min and current_pref.budget_max < pref.budget_min):
                score += 50
                matched_criteria.append("Budget (50/50)")
                
                if current_pref.habit and pref.habit:
                    common_habits = set(current_pref.habit).intersection(set(pref.habit))
                    if common_habits:
                        habit_score = (len(common_habits) / max(len(current_pref.habit), 1)) * 50
                        score += habit_score
                        matched_criteria.append(f"Habits ({round(habit_score, 1)}/50)")
                        
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
            
        return results, total
