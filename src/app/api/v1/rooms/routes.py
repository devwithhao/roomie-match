from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users.account import Account
from app.schemas.rooms.favorite import SavedPostListResponse, SavePostResponse
from app.schemas.rooms.post import PaginatedPostListOut, PostDetailOut
from app.services.rooms.favorite_service import FavoriteService
from app.services.rooms.post_service import PostService

router = APIRouter()


@router.get("", response_model=PaginatedPostListOut)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedPostListOut:
    return PostService(db).list_posts(page=page, page_size=page_size)


@router.get("/saved", response_model=SavedPostListResponse)
def list_saved_posts(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> SavedPostListResponse:
    return FavoriteService(db).list_saved_posts(account)


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
) -> PostDetailOut:
    return PostService(db).get_post_detail(post_id)


@router.post("/{post_id}/save", response_model=SavePostResponse)
def save_post(
    post_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> SavePostResponse:
    return FavoriteService(db).save_post(account, post_id)
