from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class RentalRequestCreate(BaseModel):
    start_date: date
    note: str | None = Field(default=None, max_length=1000)


class RentalRequestDecision(BaseModel):
    decision: Literal["accepted", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)


class RentalRequestOut(BaseModel):
    id: int
    account_id: int
    tenant_name: str
    tenant_email: str | None = None
    tenant_phone: str | None = None
    tenant_gender: str | None = None
    tenant_avatar_url: str | None = None
    tenant_date_of_birth: date | None = None
    tenant_address: str | None = None
    tenant_hometown: str | None = None
    tenant_bio: str | None = None
    tenant_facebook: str | None = None
    tenant_instagram: str | None = None
    tenant_twitter: str | None = None
    landlord_id: int
    room_id: int
    post_id: int
    room_title: str | None = None
    room_code: str | None = None
    post_code: str | None = None
    start_date: date
    note: str | None = None
    status: str
    decision_reason: str | None = None
    created_at: datetime


class RentalRequestListOut(BaseModel):
    items: list[RentalRequestOut]
    total: int
