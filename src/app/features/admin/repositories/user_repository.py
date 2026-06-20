from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.features.chatbot.models.chat_session import ChatSession
from app.features.matching.models.match import UserMatch
from app.features.matching.models.preference import UserPreference
from app.features.matching.models.reject import UserReject
from app.features.packages.models.entitlement import Entitlement
from app.features.packages.models.purchase import Purchase
from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.favorite import Favorite
from app.features.rooms.models.post import Post
from app.features.rooms.models.review import Review
from app.features.rooms.models.room import Room
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role
from app.features.users.role_utils import account_type_filter


class AdminUserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_roles(self) -> list[Role]:
        stmt = select(Role).order_by(Role.id.asc())
        return list(self._db.scalars(stmt).all())

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(account_type_filter(name)).order_by(Role.id.asc())
        return self._db.scalars(stmt).first()

    def get_account_row(self, account_id: int, *, for_update: bool = False) -> tuple[Account, Role, Profile | None] | None:
        stmt = (
            select(Account, Role, Profile)
            .join(Role, Account.role_id == Role.id)
            .outerjoin(Profile, Profile.account_id == Account.id)
            .where(Account.id == account_id)
            .where(Account.deleted_at.is_(None))
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self._db.execute(stmt).first()

    def get_account_by_id(self, account_id: int, *, for_update: bool = False) -> Account | None:
        stmt = select(Account).where(Account.id == account_id).where(Account.deleted_at.is_(None))
        if for_update:
            stmt = stmt.with_for_update()
        return self._db.scalars(stmt).first()

    def get_profile(self, account_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.account_id == account_id)
        return self._db.scalars(stmt).first()

    def add_account(self, account: Account) -> None:
        self._db.add(account)

    def add_profile(self, profile: Profile) -> None:
        self._db.add(profile)

    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        search: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[Account, Role, Profile | None]], int]:
        filters = [Account.deleted_at.is_(None)]
        if role:
            filters.append(account_type_filter(role))
        if status:
            filters.append(Account.status == status)
        if search:
            keyword = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Account.username).like(keyword),
                    func.lower(Account.email).like(keyword),
                )
            )

        total_stmt = select(func.count(Account.id)).join(Role, Account.role_id == Role.id).where(*filters)
        total = int(self._db.scalar(total_stmt) or 0)

        stmt = (
            select(Account, Role, Profile)
            .join(Role, Account.role_id == Role.id)
            .outerjoin(Profile, Profile.account_id == Account.id)
            .where(*filters)
            .order_by(Account.created_at.desc(), Account.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._db.execute(stmt).all()), total

    def count_by_role(self, account_type: str, *, status: str | None = None) -> int:
        stmt = (
            select(func.count(Account.id))
            .join(Role, Account.role_id == Role.id)
            .where(Account.deleted_at.is_(None))
            .where(account_type_filter(account_type))
        )
        if status:
            stmt = stmt.where(Account.status == status)
        return int(self._db.scalar(stmt) or 0)

    def count_by_status(self, status: str) -> int:
        stmt = (
            select(func.count(Account.id))
            .where(Account.deleted_at.is_(None))
            .where(Account.status == status)
        )
        return int(self._db.scalar(stmt) or 0)

    def count_all_users(self) -> int:
        stmt = select(func.count(Account.id)).where(Account.deleted_at.is_(None))
        return int(self._db.scalar(stmt) or 0)

    def count_active_admins_for_update(self) -> int:
        stmt = (
            select(Account.id)
            .join(Role, Account.role_id == Role.id)
            .where(Account.deleted_at.is_(None))
            .where(Account.status == "active")
            .where(account_type_filter("admin"))
            .with_for_update()
        )
        return len(list(self._db.scalars(stmt).all()))

    def related_counts(self, account_id: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        count_specs = {
            "rooms": (Room, Room.account_id == account_id),
            "posts": (Post, Post.account_id == account_id),
            "favorites": (Favorite, Favorite.account_id == account_id),
            "reviews": (Review, Review.account_id == account_id),
            "rental_history": (RentalHistory, RentalHistory.account_id == account_id),
            "purchases": (Purchase, Purchase.account_id == account_id),
            "entitlements": (Entitlement, Entitlement.account_id == account_id),
            "chat_sessions": (ChatSession, ChatSession.user_id == account_id),
            "matching_preferences": (UserPreference, UserPreference.account_id == account_id),
            "matching_accepts": (
                UserMatch,
                or_(UserMatch.account_id_1 == account_id, UserMatch.account_id_2 == account_id),
            ),
            "matching_rejects": (
                UserReject,
                or_(UserReject.account_id == account_id, UserReject.rejected_account_id == account_id),
            ),
            "profile": (Profile, Profile.account_id == account_id),
        }
        for key, (model, condition) in count_specs.items():
            counts[key] = int(self._db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
        return counts
