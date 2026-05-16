from __future__ import annotations

from typing import Literal

from fastapi import Query
from pydantic import BaseModel


class PostSearchFilter(BaseModel):
    city: str | None = Query(None, description="Tỉnh / Thành phố")
    district: str | None = Query(None, description="Quận / Huyện")
    ward: str | None = Query(None, description="Phường / Xã")
    room_type: str | None = Query(None, description="Loại phòng")
    min_price: int | None = Query(None, description="Giá tối thiểu")
    max_price: int | None = Query(None, description="Giá tối đa")
    amenity_ids: list[int] | None = Query(None, description="Danh sách ID tiện ích (lọc AND)")
    sort_by: Literal["newest", "price_asc", "price_desc"] = Query(
        "newest",
        description="Sắp xếp theo",
    )
