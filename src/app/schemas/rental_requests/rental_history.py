from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class RentalHistoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rental_id: int
    post_id: int
    room_id: int
    title: str | None = None
    full_address: str | None = None
    price: int | None = None
    start_date: date
    end_date: date | None = None
    rental_status: str
    can_review: bool
    can_view_post: bool = True


class RentalHistoryListResponse(BaseModel):
    items: list[RentalHistoryItemOut]
    total: int
    limit: int
    offset: int
