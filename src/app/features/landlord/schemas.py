from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LandlordRoomPayload(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    room_type: str | None = Field(default=None, max_length=100)
    area: float | None = None
    max_people: int | None = None
    current_people: int = 0
    bedroom_count: int = 1
    description: str | None = None
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    ward: str | None = Field(default=None, max_length=100)
    street: str | None = Field(default=None, max_length=255)
    full_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price: int | None = None
    electricity_price: int | None = None
    water_price: int | None = None
    internet_price: int | None = None
    parking_price: int | None = None
    deposit: int | None = None
    status: str = "available"
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_social: str | None = Field(default=None, max_length=255)
    amenities: list[str] = Field(default_factory=list)


class LandlordRoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_code: str | None = None
    code: str | None = None
    title: str | None = None
    name: str | None = None
    room_type: str | None = None
    area: float | None = None
    max_people: int | None = None
    capacity: int | None = None
    current_people: int
    bedroom_count: int
    description: str | None = None
    city: str | None = None
    district: str | None = None
    ward: str | None = None
    street: str | None = None
    full_address: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price: int | None = None
    deposit: int | None = None
    status: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_social: str | None = None
    images: list[str]
    amenities: list[str]
    created_at: datetime


class LandlordRoomListOut(BaseModel):
    items: list[LandlordRoomOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class LandlordPostCreate(BaseModel):
    room_id: int
    is_vip: bool = False
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class LandlordPostUpdate(BaseModel):
    status: str | None = None
    is_vip: bool | None = None
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class LandlordPostOut(BaseModel):
    id: int
    post_id: int
    room_id: int
    room_code: str | None = None
    code: str
    title: str | None = None
    description: str | None = None
    room_title: str | None = None
    room_description: str | None = None
    author: str | None = None
    publishedAt: str
    created_at: datetime
    status: str
    is_vip: bool
    views: int = 0
    likes: int = 0
    comments: int = 0
    boostDaysLeft: int = 0
    boostTotalDays: int = 0
    badges: list[str]
    thumbnail: str | None = None


class LandlordPostListOut(BaseModel):
    items: list[LandlordPostOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: dict[str, int]
    engagement: list[dict[str, int | str]]


class LandlordStatsOut(BaseModel):
    range: str
    total_rooms: int
    total_posts: int
    total_favorites: int
    total_contacts: int = 0
    summary: list[dict[str, int | str]]
    weeklyInteractions: list[dict[str, int | str]]
    roomStatus: list[dict[str, int | str]]
    postPerformance: list[dict[str, int | str]]
    roomDetails: list[dict[str, int | str | None]]
