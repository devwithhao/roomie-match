from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.features.users.dependencies import get_current_account
from app.database.session import get_db
from app.features.users.models.account import Account
from app.features.rental_requests.schemas.rental_history import RentalHistoryListResponse
from app.features.users.schemas.profile import MeProfileResponse, UpdateProfileIn
from app.features.rental_requests.services.rental_history_service import RentalHistoryService
from app.features.users.services.profile_service import ProfileService
from app.features.rental_requests.schemas.requests import RentalRequestListOut, RentalRequestOut
from app.features.rental_requests.services.request_service import RentalRequestService

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


@router.get("/me/rental-requests", response_model=RentalRequestListOut)
def list_my_rental_requests(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> RentalRequestListOut:
    return RentalRequestService(db).list_tenant(account)


@router.patch("/me/rental-requests/{request_id}/cancel", response_model=RentalRequestOut)
def cancel_my_rental_request(
    request_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> RentalRequestOut:
    return RentalRequestService(db).cancel(account, request_id)

