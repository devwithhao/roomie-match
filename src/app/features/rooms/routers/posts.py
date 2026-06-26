from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
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
from app.features.landlord.models import PostInteraction
from app.features.rental_requests.schemas.requests import RentalRequestCreate, RentalRequestOut
from app.features.rental_requests.services.request_service import RentalRequestService
from app.features.rooms.models.post import Post
from app.features.rooms.models.room import Room

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


@router.post("/{post_id}/rental-requests", response_model=RentalRequestOut)
def create_rental_request(
    post_id: int,
    payload: RentalRequestCreate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> RentalRequestOut:
    return RentalRequestService(db).create(account, post_id, payload)


@router.post("/{post_id}/contact-view")
def reveal_contact(
    post_id: int,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    RentalRequestService(db)._require_role(account, "tenant")
    row = db.execute(select(Post, Room).join(Room, Post.room_id == Room.id).where(Post.id == post_id, Post.status == "active")).first()
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    post, room = row
    db.add(PostInteraction(post_id=post.id, account_id=account.id, kind="contact"))
    db.commit()
    return {"name": room.contact_name, "phone": room.contact_phone, "social": room.contact_social}
    
