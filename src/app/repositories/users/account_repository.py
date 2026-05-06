from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.users.account import Account


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_email(self, email: str) -> Account | None:
        email_lower = email.strip().lower()
        stmt = (
            select(Account)
            .where(func.lower(Account.email) == email_lower)
            .where(Account.deleted_at.is_(None))
        )
        return self._db.scalars(stmt).first()

    def get_by_username(self, username: str) -> Account | None:
        stmt = (
            select(Account)
            .where(Account.username == username)
            .where(Account.deleted_at.is_(None))
        )
        return self._db.scalars(stmt).first()

    def get_by_id(self, account_id: int) -> Account | None:
        stmt = (
            select(Account)
            .where(Account.id == account_id)
            .where(Account.deleted_at.is_(None))
        )
        return self._db.scalars(stmt).first()

    def add(self, account: Account) -> None:
        self._db.add(account)
