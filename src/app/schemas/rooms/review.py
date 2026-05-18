from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Đánh giá từ 1 đến 5 sao")
    comment: str | None = Field(None, description="Bình luận")


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5, description="Đánh giá từ 1 đến 5 sao")
    comment: str | None = Field(None, description="Bình luận")


class ReviewerOut(BaseModel):
    account_id: int
    display_name: str | None = None
    avatar_url: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    rating: int | None
    comment: str | None
    created_at: datetime
    reviewer: ReviewerOut


class PaginatedReviewListOut(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
    total_pages: int
