from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.repositories.profile_repository import ProfileRepository
from app.features.users.repositories.role_repository import RoleRepository
from app.features.users.role_utils import canonical_account_type
from app.features.users.schemas.profile import (
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
                facebook=payload.facebook,
                instagram=payload.instagram,
                twitter=payload.twitter,
                zalo=payload.zalo,
                bio=payload.bio,
                date_of_birth=payload.date_of_birth,
                address=payload.address,
                hometown=payload.hometown,
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
            if payload.facebook is not None:
                profile.facebook = payload.facebook
            if payload.instagram is not None:
                profile.instagram = payload.instagram
            if payload.twitter is not None:
                profile.twitter = payload.twitter
            if payload.zalo is not None:
                profile.zalo = payload.zalo
            if payload.bio is not None:
                profile.bio = payload.bio
            if payload.date_of_birth is not None:
                profile.date_of_birth = payload.date_of_birth
            if payload.address is not None:
                profile.address = payload.address
            if payload.hometown is not None:
                profile.hometown = payload.hometown

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
        account_type = canonical_account_type(role.name, role.description) if role else "tenant"

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
                facebook=profile.facebook,
                instagram=profile.instagram,
                twitter=profile.twitter,
                zalo=profile.zalo,
                bio=profile.bio,
                date_of_birth=profile.date_of_birth,
                address=profile.address,
                hometown=profile.hometown,
            ),
        )
