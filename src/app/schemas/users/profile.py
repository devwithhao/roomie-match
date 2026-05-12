from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AccountProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    status: str
    email_verified: bool
    account_type: str


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    full_name: str
    phone: str | None = None
    gender: str | None = None
    avatar_url: str | None = None


class MeProfileResponse(BaseModel):
    account: AccountProfileOut
    profile: ProfileOut
