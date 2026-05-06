from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.models.users.role import Role
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
    return UserOut(
        id=account.id,
        email=account.email or "",
        display_name=account.username or "",
        account_type=role.name if role else "tenant",
        email_verified=bool(account.email_verified),
    )
