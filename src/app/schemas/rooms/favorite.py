from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SavedPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: int
    room_id: int
    title: str | None = None
    full_address: str | None = None
    price: int | None = None
    post_status: str
    is_vip: bool
    status: str
    saved_at: datetime


class SavePostResponse(BaseModel):
    created: bool
    post: SavedPostOut


class SavedPostListResponse(BaseModel):
    items: list[SavedPostOut]
