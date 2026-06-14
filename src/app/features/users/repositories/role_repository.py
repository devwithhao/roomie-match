from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.users.models.role import Role
from app.features.users.role_utils import account_type_filter


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self._db.scalars(stmt).first()

    def get_by_account_type(self, account_type: str) -> Role | None:
        stmt = select(Role).where(account_type_filter(account_type)).order_by(Role.id.asc())
        return self._db.scalars(stmt).first()

    def get_by_id(self, role_id: int) -> Role | None:
        return self._db.get(Role, role_id)
