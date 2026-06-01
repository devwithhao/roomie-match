from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.schemas.rental_requests.rental_history import RentalHistoryListResponse
from app.schemas.users.profile import MeProfileResponse, UpdateProfileIn
from app.services.rental_requests.rental_history_service import RentalHistoryService
from app.services.users.profile_service import ProfileService

router = APIRouter()


@router.get("/me/profile", response_model=MeProfileResponse)
def read_my_profile(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> MeProfileResponse:
    return ProfileService(db).get_my_profile(account)


@router.patch("/me/profile", response_model=MeProfileResponse)
def update_my_profile(
    payload: UpdateProfileIn,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> MeProfileResponse:
    return ProfileService(db).upsert_my_profile(account, payload)


@router.get("/me/rental-history", response_model=RentalHistoryListResponse)
def list_my_rental_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> RentalHistoryListResponse:
    return RentalHistoryService(db).list_my_rental_history(
        account,
        limit=limit,
        offset=offset,
        status=status,
        query=q,
    )

