from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.matching.match import UserMatch


class MatchRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_match(self, account_id_1: int, account_id_2: int) -> UserMatch | None:
        id_1, id_2 = sorted([account_id_1, account_id_2])
        stmt = select(UserMatch).where(
            UserMatch.account_id_1 == id_1,
            UserMatch.account_id_2 == id_2,
        )
        return self._db.scalars(stmt).first()

    def get_all_matches_for_account(self, account_id: int) -> list[UserMatch]:
        stmt = select(UserMatch).where(
            or_(
                UserMatch.account_id_1 == account_id,
                UserMatch.account_id_2 == account_id,
            )
        )
        return list(self._db.scalars(stmt).all())

    def update(self, match: UserMatch) -> None:
        self._db.add(match)

    def create_match_obj(self, account_id_1: int, account_id_2: int) -> UserMatch:
        id_1, id_2 = sorted([account_id_1, account_id_2])
        return UserMatch(account_id_1=id_1, account_id_2=id_2)
