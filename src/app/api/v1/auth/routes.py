from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.models.users.role import Role
from app.models.users.profile import Profile
from app.schemas.users.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.users.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).register(data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).login(data)


@router.get("/me", response_model=UserOut)
def read_me(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> UserOut:
    role = db.get(Role, account.role_id)
    profile = None
    try:
        profile = db.get(Profile, account.id)
    except Exception:
        profile = None
    return UserOut(
        id=account.id,
        email=account.email or "",
        display_name=account.username or "",
        account_type=role.name if role else "tenant",
        email_verified=bool(account.email_verified),
        full_name=profile.full_name if profile is not None else None,
        phone=profile.phone if profile is not None else None,
        gender=profile.gender if profile is not None else None,
        avatar_url=profile.avatar_url if profile is not None else None,
        joined_at=account.created_at if getattr(account, "created_at", None) is not None else None,
    )
