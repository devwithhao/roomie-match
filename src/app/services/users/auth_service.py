from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.users.account import Account
from app.repositories.users.account_repository import AccountRepository
from app.repositories.users.role_repository import RoleRepository
from app.schemas.users.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


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


def _mysql_errno_from_blob(blob: str) -> int | None:
    m = re.search(r"\b(1062|1452|1216|1217)\b", blob)
    if m:
        return int(m.group(1))
    return None


def _is_mysql_duplicate_key(exc: IntegrityError) -> bool:
    blob = _integrity_error_blob(exc).lower()
    if _mysql_errno_from_blob(blob) == 1062:
        return True
    return "duplicate entry" in blob or "duplicate key" in blob


def _is_foreign_key_violation(exc: IntegrityError) -> bool:
    blob = _integrity_error_blob(exc).lower()
    if _mysql_errno_from_blob(blob) == 1452:
        return True
    return "foreign key constraint" in blob or "cannot add or update a child row" in blob


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._accounts = AccountRepository(db)
        self._roles = RoleRepository(db)

    def register(self, data: RegisterRequest) -> TokenResponse:
        role = self._roles.get_by_name(data.account_type.value)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role configuration missing",
            )

        email_key = _normalize_email(str(data.email))
        if self._accounts.get_by_email(email_key):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if self._accounts.get_by_username(data.display_name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Display name already taken",
            )

        account = Account(
            email=email_key,
            username=data.display_name,
            password_hash=hash_password(data.password),
            role_id=role.id,
        )
        self._accounts.add(account)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if _is_mysql_duplicate_key(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email or display name already exists",
                ) from None
            if _is_foreign_key_violation(exc):
                logging.getLogger(__name__).warning(
                    "Register FK failure (roles seed?): %s",
                    _integrity_error_blob(exc),
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "Invalid role reference: check that table `roles` has "
                        "tenant/landlord (run alembic upgrade head)."
                    ),
                ) from None
            logging.getLogger(__name__).exception(
                "Register unexpected integrity error: %s",
                _integrity_error_blob(exc),
            )
            detail = "Registration failed (database constraint)"
            if settings.app_debug:
                detail = f"{detail}: {_integrity_error_blob(exc)[:800]}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail,
            ) from exc
        self._db.refresh(account)
        return self._token_response(account, role.name)

    def login(self, data: LoginRequest) -> TokenResponse:
        account = self._accounts.get_by_email(_normalize_email(str(data.email)))
        if account is None or account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not account.password_hash or not verify_password(
            data.password,
            account.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        role = self._roles.get_by_id(account.role_id)
        role_name = role.name if role else "tenant"

        account.last_login_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(account)
        return self._token_response(account, role_name)

    def _token_response(self, account: Account, role_name: str) -> TokenResponse:
        token, expires_in = create_access_token(
            subject_id=account.id,
            email=account.email or "",
            role_name=role_name,
        )
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserOut(
                id=account.id,
                email=account.email or "",
                display_name=account.username or "",
                account_type=role_name,
                email_verified=bool(account.email_verified),
            ),
        )