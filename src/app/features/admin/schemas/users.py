from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


UserRoleName = Literal["admin", "landlord", "tenant"]
UserStatus = Literal["active", "blocked"]


class AdminUserRoleOption(BaseModel):
    value: str
    label: str


class AdminUserStatusOption(BaseModel):
    value: str
    label: str


class AdminUserMetaResponse(BaseModel):
    roles: list[AdminUserRoleOption]
    statuses: list[AdminUserStatusOption]


class AdminUserStatsResponse(BaseModel):
    total_admins: int
    active_admins: int
    total_users: int
    landlords: int
    tenants: int
    active_users: int
    blocked_users: int


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    phone: str | None = None
    role: str
    role_label: str
    status: str
    status_label: str
    email_verified: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserOut]
    total: int
    total_pages: int
    page: int
    page_size: int


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRoleName
    status: UserStatus = "active"


class AdminUpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRoleName | None = None
    status: UserStatus | None = None
    expected_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_at_least_one_change(self) -> "AdminUpdateUserRequest":
        if (
            self.username is None
            and self.email is None
            and self.phone is None
            and self.password is None
            and self.role is None
            and self.status is None
            and self.expected_updated_at is None
        ):
            raise ValueError("At least one field must be provided")
        return self


class AdminUpdateUserStatusRequest(BaseModel):
    status: UserStatus
    expected_updated_at: datetime | None = None


class AdminDeleteUserResponse(BaseModel):
    success: bool
    id: int
    message: str

