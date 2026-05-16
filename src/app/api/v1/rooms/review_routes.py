from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.schemas.rooms.review import (
    PaginatedReviewListOut,
    ReviewCreate,
    ReviewOut,
    ReviewUpdate,
)
from app.services.rooms.review_service import ReviewService

router = APIRouter()


@router.get("/{room_id}/reviews", response_model=PaginatedReviewListOut)
def list_reviews(
    room_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedReviewListOut:
    return ReviewService(db).list_reviews(room_id, page=page, page_size=page_size)


@router.post("/{room_id}/reviews", response_model=ReviewOut)
def add_review(
    room_id: int,
    data: ReviewCreate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> ReviewOut:
    return ReviewService(db).add_review(account, room_id, data)


@router.put("/{room_id}/reviews/{review_id}", response_model=ReviewOut)
def update_review(
    room_id: int,
    review_id: int,
    data: ReviewUpdate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> ReviewOut:
    return ReviewService(db).update_review(account, room_id, review_id, data)
