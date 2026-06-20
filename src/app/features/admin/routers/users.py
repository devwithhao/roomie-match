from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.admin.schemas.users import (
    AdminCreateUserRequest,
    AdminDeleteUserResponse,
    AdminUpdateUserRequest,
    AdminUpdateUserStatusRequest,
    AdminUserListResponse,
    AdminUserMetaResponse,
    AdminUserOut,
    AdminUserStatsResponse,
    UserRoleName,
    UserStatus,
)
from app.features.admin.services.user_service import AdminUserService
from app.features.users.models.account import Account

router = APIRouter()


@router.get("/dashboard")
def get_admin_dashboard(
    admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> dict:
    return AdminUserService(db).get_dashboard(admin)


@router.get("/users/meta", response_model=AdminUserMetaResponse)
def get_user_meta(
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserMetaResponse:
    return AdminUserService(db).get_meta()


@router.get("/users/stats", response_model=AdminUserStatsResponse)
def get_user_stats(
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserStatsResponse:
    return AdminUserService(db).get_stats()


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    role: UserRoleName | None = Query(default=None),
    user_status: UserStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=100),
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    return AdminUserService(db).list_users(
        role=role,
        user_status=user_status,
        search=q,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserOut)
def get_user_detail(
    user_id: int,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    return AdminUserService(db).get_user(user_id)


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    return AdminUserService(db).create_user(payload)


@router.put("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    return AdminUserService(db).update_user(user_id, payload, admin)


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
def update_user_status(
    user_id: int,
    payload: AdminUpdateUserStatusRequest,
    admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    return AdminUserService(db).update_user_status(user_id, payload, admin)


@router.delete("/users/{user_id}", response_model=AdminDeleteUserResponse)
def delete_user(
    user_id: int,
    admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminDeleteUserResponse:
    return AdminUserService(db).delete_user(user_id, admin)
