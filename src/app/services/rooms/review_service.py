from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.rooms.review import Review
from app.models.users.account import Account
from app.repositories.rooms.review_repository import ReviewRepository
from app.repositories.rooms.room_repository import RoomRepository
from app.schemas.rooms.review import (
    PaginatedReviewListOut,
    ReviewCreate,
    ReviewerOut,
    ReviewOut,
    ReviewUpdate,
)
from app.shared.pagination.paginator import PageParams, total_pages


class ReviewService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._reviews = ReviewRepository(db)
        self._rooms = RoomRepository(db)

    def list_reviews(
        self,
        room_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedReviewListOut:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        params = PageParams(page=page, page_size=page_size)

        total = self._reviews.count_by_room(room_id)
        rows = self._reviews.list_by_room(room_id, params)

        items = []
        for review, account in rows:
            reviewer = ReviewerOut(
                account_id=account.id,
                display_name=account.username,
                avatar_url=account.avatar_url,
            )
            items.append(
                ReviewOut(
                    id=review.id,
                    room_id=review.room_id,
                    rating=review.rating,
                    comment=review.comment,
                    created_at=review.created_at,
                    reviewer=reviewer,
                )
            )

        return PaginatedReviewListOut(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def add_review(
        self,
        account: Account,
        room_id: int,
        data: ReviewCreate,
    ) -> ReviewOut:
        room = self._rooms.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found",
            )

        existing = self._reviews.get_by_account_and_room(account.id, room_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this room. Please edit your existing review.",
            )

        review = Review(
            account_id=account.id,
            room_id=room_id,
            rating=data.rating,
            comment=data.comment,
        )
        self._reviews.add(review)
        self._db.commit()
        self._db.refresh(review)

        reviewer = ReviewerOut(
            account_id=account.id,
            display_name=account.username,
            avatar_url=account.avatar_url,
        )
        return ReviewOut(
            id=review.id,
            room_id=review.room_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            reviewer=reviewer,
        )

    def update_review(
        self,
        account: Account,
        room_id: int,
        review_id: int,
        data: ReviewUpdate,
    ) -> ReviewOut:
        review = self._reviews.get_by_id(review_id)
        if not review or review.room_id != room_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )

        if review.account_id != account.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own review",
            )

        if data.rating is not None:
            review.rating = data.rating
        if data.comment is not None:
            review.comment = data.comment

        self._db.commit()
        self._db.refresh(review)

        reviewer = ReviewerOut(
            account_id=account.id,
            display_name=account.username,
            avatar_url=account.avatar_url,
        )
        return ReviewOut(
            id=review.id,
            room_id=review.room_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            reviewer=reviewer,
        )
