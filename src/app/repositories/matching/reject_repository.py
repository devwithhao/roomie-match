from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.matching.reject import UserReject


class RejectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_reject(self, account_id: int, rejected_account_id: int) -> UserReject | None:
        stmt = select(UserReject).where(
            UserReject.account_id == account_id,
            UserReject.rejected_account_id == rejected_account_id,
        )
        return self._db.scalars(stmt).first()

    def get_rejects_by_account(self, account_id: int) -> list[UserReject]:
        stmt = select(UserReject).where(UserReject.account_id == account_id)
        return list(self._db.scalars(stmt).all())

    def update(self, reject: UserReject) -> None:
        self._db.add(reject)
