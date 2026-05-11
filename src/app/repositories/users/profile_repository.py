from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users.profile import Profile


class ProfileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_account_id(self, account_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.account_id == account_id)
        return self._db.scalars(stmt).first()
