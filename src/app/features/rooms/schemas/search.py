from __future__ import annotations

from typing import Literal

from fastapi import Query
from pydantic import BaseModel


class PostSearchFilter(BaseModel):
    city: str | None = Query(None, description="City")
    district: str | None = Query(None, description="District")
    ward: str | None = Query(None, description="Ward")
    room_type: str | None = Query(None, description="Room type")
    min_price: int | None = Query(None, description="Minimum price")
    max_price: int | None = Query(None, description="Maximum price")
    amenity_ids: list[int] | None = Query(None, description="Amenity IDs to match")
    sort_by: Literal["newest", "price_asc", "price_desc"] = Query(
        "newest",
        description="Sort by",
    )
