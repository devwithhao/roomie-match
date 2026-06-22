from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class PostModerationUpdate(BaseModel):
    status: Literal["active", "approved", "rejected", "closed"]
    reason: str | None = Field(default=None, max_length=1000)


class RoomModerationUpdate(BaseModel):
    status: Literal["available", "rented", "archived"]


class VerificationModerationUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)
