from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.schemas.rooms.favorite import (
    SavedPostListResponse,
    SavePostResponse,
    UnsavePostResponse,
)
from app.services.rooms.favorite_service import FavoriteService

router = APIRouter()


@router.post("/{post_id}/save", response_model=SavePostResponse)
def save_post(
    post_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> SavePostResponse:
    return FavoriteService(db).save_post(account, post_id)


@router.delete("/{post_id}/save", response_model=UnsavePostResponse)
def unsave_post(
    post_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> UnsavePostResponse:
    return FavoriteService(db).unsave_post(account, post_id)


@router.get("/saved", response_model=SavedPostListResponse)
def list_saved_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> SavedPostListResponse:
    return FavoriteService(db).list_saved_posts(account, limit=limit, offset=offset)
