from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    gender: Literal["male", "female", "other"] | None = None
    avatar_url: str | None = None


class UpdateProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    gender: Literal["male", "female", "other"] | None = Field(default=None)
    avatar_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateProfileIn":
        if (
            self.full_name is None
            and self.phone is None
            and self.gender is None
            and self.avatar_url is None
        ):
            raise ValueError("At least one field must be provided")
        return self


class MeProfileResponse(BaseModel):
    account: AccountProfileOut
    profile: ProfileOut
