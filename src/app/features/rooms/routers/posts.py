from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.features.users.dependencies import get_current_account
from app.database.session import get_db
from app.features.users.models.account import Account

from app.features.rooms.schemas.post import PaginatedPostListOut, PostDetailOut
from app.features.rooms.schemas.search import PostSearchFilter
from app.features.rooms.schemas.favorite import (
    SavedPostListResponse,
    SavePostResponse,
    UnsavePostResponse,
)
from app.features.rooms.services.favorite_service import FavoriteService
from app.features.rooms.services.post_service import PostService

router = APIRouter()


@router.get("", response_model=PaginatedPostListOut)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    filters: PostSearchFilter = Depends(),
    db: Session = Depends(get_db),
) -> PaginatedPostListOut:
    return PostService(db).list_posts(page=page, page_size=page_size, filters=filters)


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
    
