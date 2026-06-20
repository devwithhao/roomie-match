from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.features.admin.repositories.user_repository import AdminUserRepository
from app.features.admin.schemas.users import (
    AdminCreateUserRequest,
    AdminDeleteUserResponse,
    AdminUpdateUserRequest,
    AdminUpdateUserStatusRequest,
    AdminUserListResponse,
    AdminUserMetaResponse,
    AdminUserOut,
    AdminUserRoleOption,
    AdminUserStatsResponse,
    AdminUserStatusOption,
)
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.role_utils import account_type_label, canonical_account_type
from app.shared.pagination.paginator import PageParams, total_pages


STATUS_LABELS = {
    "active": "Đang hoạt động",
    "blocked": "Bị khóa",
    "deleted": "Đã xóa",
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _integrity_error_blob(exc: IntegrityError) -> str:
    parts = [str(exc), repr(exc)]
    if exc.orig is not None:
        parts.append(str(exc.orig))
        parts.append(repr(exc.orig))
        oargs = getattr(exc.orig, "args", ())
        if oargs:
            parts.extend(str(a) for a in oargs)
    return "\n".join(parts)


def _is_duplicate_key(exc: IntegrityError) -> bool:
    blob = _integrity_error_blob(exc).lower()
    return bool(re.search(r"\b1062\b", blob)) or "duplicate entry" in blob or "duplicate key" in blob


def _same_timestamp(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return True
    return left.replace(tzinfo=None, microsecond=0) == right.replace(tzinfo=None, microsecond=0)


class AdminUserService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = AdminUserRepository(db)

    def get_meta(self) -> AdminUserMetaResponse:
        roles = self._users.list_roles()
        seen: set[str] = set()
        options: list[AdminUserRoleOption] = []
        for role in roles:
            account_type = canonical_account_type(role.name, role.description)
            if account_type not in {"admin", "landlord", "tenant"} or account_type in seen:
                continue
            seen.add(account_type)
            options.append(
                AdminUserRoleOption(
                    value=account_type,
                    label=account_type_label(account_type, role.description),
                )
            )
        return AdminUserMetaResponse(
            roles=options,
            statuses=[
                AdminUserStatusOption(value="active", label=STATUS_LABELS["active"]),
                AdminUserStatusOption(value="blocked", label=STATUS_LABELS["blocked"]),
            ],
        )

    def get_stats(self) -> AdminUserStatsResponse:
        return AdminUserStatsResponse(
            total_admins=self._users.count_by_role("admin"),
            active_admins=self._users.count_by_role("admin", status="active"),
            total_users=self._users.count_all_users(),
            landlords=self._users.count_by_role("landlord"),
            tenants=self._users.count_by_role("tenant"),
            active_users=self._users.count_by_status("active"),
            blocked_users=self._users.count_by_status("blocked"),
        )

    def get_dashboard(self, current_admin: Account) -> dict:
        stats = self.get_stats()
        return {
            "currentUser": {
                "name": current_admin.username or current_admin.email or "Admin",
                "initials": (current_admin.username or "AD")[:2].upper(),
            },
            "pageHeader": {
                "title": "Tổng quan",
                "highlight": "quan",
                "subtitle": "Theo dõi dữ liệu quản trị từ hệ thống RoomieMatch",
            },
            "stats": [
                {
                    "id": "users",
                    "label": "Tổng người dùng",
                    "value": stats.total_users,
                    "trend": "up",
                    "trendLabel": "DB",
                    "changeLabel": "Dữ liệu từ cơ sở dữ liệu",
                    "icon": "users",
                    "linkLabel": "Xem chi tiết",
                    "isPrimary": True,
                },
                {
                    "id": "landlords",
                    "label": account_type_label("landlord"),
                    "value": stats.landlords,
                    "trend": "up",
                    "trendLabel": "DB",
                    "changeLabel": "Tài khoản chủ trọ hiện có",
                    "icon": "building",
                    "linkLabel": "Xem chi tiết",
                },
                {
                    "id": "tenants",
                    "label": account_type_label("tenant"),
                    "value": stats.tenants,
                    "trend": "up",
                    "trendLabel": "DB",
                    "changeLabel": "Tài khoản khách thuê hiện có",
                    "icon": "users",
                    "linkLabel": "Xem chi tiết",
                },
            ],
            "performance": {
                "title": "Hiệu suất",
                "years": ["2026"],
                "labels": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"],
                "seriesByYear": {"2026": []},
            },
            "staff": [],
            "regions": [],
            "notifications": [],
        }

    def list_users(
        self,
        *,
        role: str | None,
        user_status: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminUserListResponse:
        params = PageParams(page=page, page_size=page_size)
        rows, total = self._users.list_users(
            role=role,
            status=user_status,
            search=search,
            offset=params.offset,
            limit=params.limit,
        )
        return AdminUserListResponse(
            items=[self._to_user_out(*row) for row in rows],
            total=total,
            total_pages=max(1, total_pages(total, page_size)),
            page=page,
            page_size=page_size,
        )

    def get_user(self, user_id: int) -> AdminUserOut:
        row = self._users.get_account_row(user_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._to_user_out(*row)

    def create_user(self, payload: AdminCreateUserRequest) -> AdminUserOut:
        role = self._get_role_or_422(payload.role)
        account = Account(
            email=_normalize_email(str(payload.email)),
            username=payload.username.strip(),
            password_hash=hash_password(payload.password),
            role_id=role.id,
            status=payload.status,
            email_verified=False,
        )
        self._users.add_account(account)
        try:
            self._db.flush()
            self._users.add_profile(
                Profile(
                    account_id=account.id,
                    full_name=account.username or str(payload.email),
                    phone=payload.phone.strip() if payload.phone else None,
                )
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if _is_duplicate_key(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email or username already exists",
                ) from None
            raise

        row = self._users.get_account_row(account.id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Created user not found")
        return self._to_user_out(*row)

    def update_user(
        self,
        user_id: int,
        payload: AdminUpdateUserRequest,
        current_admin: Account,
    ) -> AdminUserOut:
        row = self._users.get_account_row(user_id, for_update=True)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        account, current_role, profile = row
        self._ensure_not_stale(account, payload.expected_updated_at)

        next_role = current_role
        if payload.role is not None:
            next_role = self._get_role_or_422(payload.role)

        next_status = payload.status or account.status
        self._validate_admin_transition(
            account=account,
            current_role_name=canonical_account_type(current_role.name, current_role.description),
            next_role_name=canonical_account_type(next_role.name, next_role.description),
            next_status=next_status,
            current_admin=current_admin,
        )

        if payload.username is not None:
            account.username = payload.username.strip()
        if payload.email is not None:
            account.email = _normalize_email(str(payload.email))
        if payload.password is not None:
            account.password_hash = hash_password(payload.password)
        account.role_id = next_role.id
        account.status = next_status

        if payload.phone is not None:
            phone = payload.phone.strip() or None
            if profile is None:
                profile = Profile(account_id=account.id, full_name=account.username or account.email or "User", phone=phone)
                self._users.add_profile(profile)
            else:
                profile.phone = phone

        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if _is_duplicate_key(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email or username already exists",
                ) from None
            raise

        row = self._users.get_account_row(user_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._to_user_out(*row)

    def update_user_status(
        self,
        user_id: int,
        payload: AdminUpdateUserStatusRequest,
        current_admin: Account,
    ) -> AdminUserOut:
        return self.update_user(
            user_id,
            AdminUpdateUserRequest(status=payload.status, expected_updated_at=payload.expected_updated_at),
            current_admin,
        )

    def delete_user(self, user_id: int, current_admin: Account) -> AdminDeleteUserResponse:
        row = self._users.get_account_row(user_id, for_update=True)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        account, role, _profile = row
        if account.id == current_admin.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin cannot delete their own account")
        if canonical_account_type(role.name, role.description) == "admin" and account.status == "active":
            self._ensure_another_active_admin()

        # Intentionally inspect relations before deletion. Soft delete keeps these
        # rows intact, so FK integrity and historical records remain safe.
        self._users.related_counts(account.id)
        account.status = "deleted"
        account.deleted_at = datetime.now(timezone.utc)
        self._db.commit()
        return AdminDeleteUserResponse(
            success=True,
            id=account.id,
            message="User has been deleted",
        )

    def _get_role_or_422(self, role_name: str):
        role = self._users.get_role_by_name(role_name)
        if role is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid role")
        return role

    def _ensure_not_stale(self, account: Account, expected_updated_at: datetime | None) -> None:
        if expected_updated_at is not None and not _same_timestamp(account.updated_at, expected_updated_at):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User was updated by another request. Please reload and try again.",
            )

    def _validate_admin_transition(
        self,
        *,
        account: Account,
        current_role_name: str,
        next_role_name: str,
        next_status: str,
        current_admin: Account,
    ) -> None:
        if account.id == current_admin.id and next_status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin cannot lock their own account")
        if account.id == current_admin.id and next_role_name != "admin":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin cannot remove their own admin role")

        removes_active_admin = current_role_name == "admin" and account.status == "active" and (
            next_role_name != "admin" or next_status != "active"
        )
        if removes_active_admin:
            self._ensure_another_active_admin()

    def _ensure_another_active_admin(self) -> None:
        if self._users.count_active_admins_for_update() <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one active admin account is required",
            )

    def _to_user_out(self, account: Account, role, profile: Profile | None) -> AdminUserOut:
        account_type = canonical_account_type(role.name, role.description)
        return AdminUserOut(
            id=account.id,
            username=account.username or "",
            email=account.email or "",
            phone=profile.phone if profile is not None else None,
            role=account_type,
            role_label=account_type_label(account_type, role.description),
            status=account.status,
            status_label=STATUS_LABELS.get(account.status, account.status),
            email_verified=bool(account.email_verified),
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_login_at=account.last_login_at,
        )
