from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.users.account import Account
from app.repositories.users.profile_repository import ProfileRepository
from app.repositories.users.role_repository import RoleRepository
from app.schemas.users.profile import AccountProfileOut, MeProfileResponse, ProfileOut


class ProfileService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._profiles = ProfileRepository(db)
        self._roles = RoleRepository(db)

    def get_my_profile(self, account: Account) -> MeProfileResponse:
        profile = self._profiles.get_by_account_id(account.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

        role = self._roles.get_by_id(account.role_id)
        account_type = role.name if role else "tenant"

        return MeProfileResponse(
            account=AccountProfileOut(
                id=account.id,
                email=account.email or "",
                username=account.username,
                status=account.status,
                email_verified=bool(account.email_verified),
                account_type=account_type,
            ),
            profile=ProfileOut(
                account_id=profile.account_id,
                full_name=profile.full_name,
                phone=profile.phone,
                gender=profile.gender,
                avatar_url=profile.avatar_url,
            ),
        )
