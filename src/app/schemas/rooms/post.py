from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: int
    room_id: int
    title: str | None = None
    thumbnail: str | None = None
    price: int | None = None
    room_type: str | None = None
    area: float | None = None
    district: str | None = None
    ward: str | None = None
    created_at: datetime
    is_vip: bool
    status: str
    bedroom_count: int


class PaginatedPostListOut(BaseModel):
    items: list[PostCardOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str


class AmenityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None = None


class LandlordOut(BaseModel):
    account_id: int
    display_name: str | None = None
    avatar_url: str | None = None
    contact_phone: str | None = None
    contact_social: str | None = None


class RoomDetailOut(BaseModel):
    room_id: int
    title: str | None = None
    description: str | None = None
    price: int | None = None
    deposit: int | None = None
    area: float | None = None
    max_people: int | None = None
    current_people: int
    room_type: str | None = None
    city: str | None = None
    district: str | None = None
    ward: str | None = None
    street: str | None = None
    full_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    electricity_price: int | None = None
    water_price: int | None = None
    internet_price: int | None = None
    parking_price: int | None = None


class PostDetailOut(BaseModel):
    post_id: int
    created_at: datetime
    is_vip: bool
    status: str
    room: RoomDetailOut
    images: list[ImageOut]
    amenities: list[AmenityOut]
    landlord: LandlordOut
