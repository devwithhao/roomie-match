from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from app.core.config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(
    *,
    subject_id: int,
    email: str,
    role_name: str,
) -> tuple[str, int]:
    expire_minutes = settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(subject_id),
        "email": email,
        "role": role_name,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )
    return token, expire_minutes * 60


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
    )


def decode_access_token_safe(token: str) -> dict | None:
    try:
        return decode_access_token(token)
    except PyJWTError:
        return None
