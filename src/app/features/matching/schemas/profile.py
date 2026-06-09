from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateMatchingProfileRequest(BaseModel):
    image: str | None = Field(default=None, description="Avatar URL or Image string")
    introduce: str | None = Field(default=None, description="Introduction text")
    habit: list[str] | None = Field(default=None, description="List of habits")
    location: str | None = Field(default=None, description="Target location/city")
    budget: str | None = Field(default=None, description="Budget string in format minbudget-maxbudget")


class MatchingProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    email: str | None = None
    phone: str | None = None
    facebook: str | None = None
    instagram: str | None = None
    twitter: str | None = None
    image: str | None = None
    introduce: str | None = None
    habit: list[str] | None = None
    location: str | None = None
    budget: str | None = None
