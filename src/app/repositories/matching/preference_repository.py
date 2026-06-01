from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.matching.preference import UserPreference


class PreferenceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_account_id(self, account_id: int) -> UserPreference | None:
        stmt = select(UserPreference).where(UserPreference.account_id == account_id)
        return self._db.scalars(stmt).first()

    def update(self, preference: UserPreference) -> None:
        self._db.add(preference)
