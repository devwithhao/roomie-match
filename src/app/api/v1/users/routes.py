from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.schemas.users.profile import MeProfileResponse
from app.services.users.profile_service import ProfileService

router = APIRouter()


@router.get("/me/profile", response_model=MeProfileResponse)
def read_my_profile(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> MeProfileResponse:
    return ProfileService(db).get_my_profile(account)
