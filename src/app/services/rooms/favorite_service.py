from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.rooms.favorite import Favorite
from app.models.rooms.post import Post
from app.models.rooms.room import Room
from app.models.users.account import Account
from app.repositories.rooms.favorite_repository import FavoriteRepository
from app.repositories.rooms.post_repository import PostRepository
from app.repositories.users.role_repository import RoleRepository
from app.schemas.rooms.favorite import SavedPostListResponse, SavedPostOut, SavePostResponse


class FavoriteService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._posts = PostRepository(db)
        self._favorites = FavoriteRepository(db)
        self._roles = RoleRepository(db)

    def save_post(self, account: Account, post_id: int) -> SavePostResponse:
        self._ensure_tenant(account)
        post = self._posts.get_by_id(post_id)
        if post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        favorite = self._favorites.get_by_account_and_post(account.id, post_id)
        created = False
        if favorite is None:
            favorite = Favorite(account_id=account.id, post_id=post_id)
            self._favorites.add(favorite)
            try:
                self._db.commit()
            except IntegrityError:
                self._db.rollback()
                favorite = self._favorites.get_by_account_and_post(account.id, post_id)
            else:
                created = True

        if favorite is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save room",
            )

        row = self._favorites.list_saved_posts(account.id)
        match = next((r for r in row if r[0].id == post.id), None)
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch saved post",
            )
        saved_post = self._build_saved_post_out(match[0], match[1], favorite.created_at)
        return SavePostResponse(created=created, post=saved_post)

    def list_saved_posts(self, account: Account) -> SavedPostListResponse:
        self._ensure_tenant(account)
        rows = self._favorites.list_saved_posts(account.id)
        items = [
            self._build_saved_post_out(post, room, saved_at)
            for post, room, saved_at in rows
        ]
        return SavedPostListResponse(items=items)

    def _ensure_tenant(self, account: Account) -> None:
        role = self._roles.get_by_id(account.role_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role configuration missing",
            )
        if role.name != "tenant":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant accounts can save rooms",
            )

    def _build_saved_post_out(self, post: Post, room: Room, saved_at) -> SavedPostOut:
        return SavedPostOut(
            post_id=post.id,
            room_id=room.id,
            title=room.title,
            full_address=room.full_address,
            price=room.price,
            post_status=post.status,
            is_vip=post.is_vip,
            status=room.status,
            saved_at=saved_at,
        )
