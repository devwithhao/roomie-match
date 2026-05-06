from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users.role import Role


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self._db.scalars(stmt).first()

    def get_by_id(self, role_id: int) -> Role | None:
        return self._db.get(Role, role_id)
