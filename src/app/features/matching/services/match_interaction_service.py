from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.matching.models.match import UserMatch
from app.features.matching.models.reject import UserReject
from app.features.users.models.profile import Profile
from app.features.users.models.account import Account
from app.features.matching.models.preference import UserPreference
from app.features.matching.repositories.match_repository import MatchRepository
from app.features.matching.repositories.reject_repository import RejectRepository
from app.features.matching.schemas.schemas import MatchHistoryItem, RejectHistoryItem, MatchContact, MatchContactSocials

class MatchInteractionService:
    def __init__(self, db: Session):
        self.db = db
        self.matches = MatchRepository(db)
        self.rejects = RejectRepository(db)

    def accept_user(self, current_account_id: int, target_account_id: int) -> dict:
        if current_account_id == target_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot match yourself.")
            
        match = self.matches.get_match(current_account_id, target_account_id)
        if not match:
            match = self.matches.create_match_obj(current_account_id, target_account_id)
            
        match.is_matched = True
        self.matches.update(match)
        self.db.commit()
        
        return {"detail": "Match accepted successfully."}

    def unmatch_user(self, current_account_id: int, target_account_id: int) -> dict:
        match = self.matches.get_match(current_account_id, target_account_id)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
            
        match.is_matched = False
        self.matches.update(match)
        self.db.commit()
        
        return {"detail": "Unmatched successfully."}

    def reject_user(self, current_account_id: int, target_account_id: int) -> dict:
        if current_account_id == target_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reject yourself.")
            
        reject = self.rejects.get_reject(current_account_id, target_account_id)
        if not reject:
            reject = UserReject(account_id=current_account_id, rejected_account_id=target_account_id)
            self.rejects.update(reject)
            self.db.commit()
            
        return {"detail": "User rejected successfully."}

    def get_reject_history(self, current_account_id: int) -> list[RejectHistoryItem]:
        rejects = self.rejects.get_rejects_by_account(current_account_id)
        results = []
        for r in rejects:
            profile = self.db.scalar(select(Profile).where(Profile.account_id == r.rejected_account_id))
            account = self.db.scalar(select(Account).where(Account.id == r.rejected_account_id))
            pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == r.rejected_account_id))
            
            if profile and account:
                contact = MatchContact(
                    email=account.email or "",
                    phone=profile.phone or "",
                    socials=MatchContactSocials()
                )
                joined_at = profile.created_at.strftime("%d/%m/%Y") if profile.created_at else ""
                area_val = ""
                if pref:
                    area_val = pref.target_district or pref.target_city or ""
                    
                results.append(RejectHistoryItem(
                    id=f"m-{r.rejected_account_id:02d}",
                    name=profile.full_name,
                    area=area_val,
                    joinedAt=joined_at,
                    avatar=profile.avatar_url,
                    contact=contact,
                    account_id=r.rejected_account_id,
                    full_name=profile.full_name,
                    avatar_url=profile.avatar_url,
                    rejected_at=r.created_at,
                ))
        return results

    def get_match_history(self, current_account_id: int) -> list[MatchHistoryItem]:
        matches = self.matches.get_all_matches_for_account(current_account_id)
        results = []
        for m in matches:
            target_id = m.account_id_2 if m.account_id_1 == current_account_id else m.account_id_1
            profile = self.db.scalar(select(Profile).where(Profile.account_id == target_id))
            account = self.db.scalar(select(Account).where(Account.id == target_id))
            pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == target_id))
            
            if profile and account:
                contact = MatchContact(
                    email=account.email or "",
                    phone=profile.phone or "",
                    socials=MatchContactSocials()
                )
                joined_at = profile.created_at.strftime("%d/%m/%Y") if profile.created_at else ""
                area_val = ""
                if pref:
                    area_val = pref.target_district or pref.target_city or ""
                    
                results.append(MatchHistoryItem(
                    id=f"m-{target_id:02d}",
                    name=profile.full_name,
                    area=area_val,
                    joinedAt=joined_at,
                    avatar=profile.avatar_url,
                    contact=contact,
                    account_id=target_id,
                    full_name=profile.full_name,
                    avatar_url=profile.avatar_url,
                    matched_at=m.created_at,
                    is_matched=m.is_matched,
                ))
        return results
