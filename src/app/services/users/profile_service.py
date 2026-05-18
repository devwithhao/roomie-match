from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.users.account import Account
from app.models.users.profile import Profile
from app.repositories.users.profile_repository import ProfileRepository
from app.repositories.users.role_repository import RoleRepository
from app.schemas.users.profile import (
    AccountProfileOut,
    MeProfileResponse,
    ProfileOut,
    UpdateProfileIn,
)


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
        return self._build_profile_response(account, profile)

    def upsert_my_profile(
        self,
        account: Account,
        payload: UpdateProfileIn,
    ) -> MeProfileResponse:
        profile = self._profiles.get_by_account_id(account.id)
        if profile is None:
            if payload.full_name is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="full_name is required when creating profile",
                )
            profile = Profile(
                account_id=account.id,
                full_name=payload.full_name,
                phone=payload.phone,
                gender=payload.gender,
                avatar_url=payload.avatar_url,
            )
        else:
            if payload.full_name is not None:
                profile.full_name = payload.full_name
            if payload.phone is not None:
                profile.phone = payload.phone
            if payload.gender is not None:
                profile.gender = payload.gender
            if payload.avatar_url is not None:
                profile.avatar_url = payload.avatar_url

        self._profiles.update(profile)
        self._db.commit()
        self._db.refresh(profile)
        return self._build_profile_response(account, profile)

    def _build_profile_response(
        self,
        account: Account,
        profile: Profile,
    ) -> MeProfileResponse:
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
