from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountType(str, Enum):
    tenant = "tenant"
    landlord = "landlord"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(
        min_length=1,
        max_length=100,
        description=(
            "Ten hien thi (tren form dang ky). Tam luu o DB cot accounts.username; "
            "sau se chuyen sang profile khi co module profile."
        ),
    )
    account_type: AccountType


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    account_type: str
    email_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
