from __future__ import annotations

from sqlalchemy.orm import Session

from app.features.users.models.account import Account
from app.features.rental_requests.repositories.rental_history_repository import (
    RentalHistoryRepository,
)
from app.features.rental_requests.schemas.rental_history import (
    RentalHistoryItemOut,
    RentalHistoryListResponse,
)


class RentalHistoryService:
    def __init__(self, db: Session) -> None:
        self._repo = RentalHistoryRepository(db)

    def list_my_rental_history(
        self,
        account: Account,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        query: str | None = None,
    ) -> RentalHistoryListResponse:
        total = self._repo.count_by_account(
            account.id,
            status=status,
            query=query,
        )
        rows = self._repo.list_by_account(
            account.id,
            limit=limit,
            offset=offset,
            status=status,
            query=query,
        )

        items = [
            RentalHistoryItemOut(
                rental_id=history.id,
                post_id=post.id,
                room_id=room.id,
                title=room.title,
                full_address=room.full_address,
                price=room.price,
                start_date=history.start_date,
                end_date=history.end_date,
                rental_status=history.status,
                can_review=history.status in {"completed", "ended"},
                can_view_post=True,
            )
            for history, room, post in rows
        ]

        return RentalHistoryListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
