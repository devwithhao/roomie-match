from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.landlord.dependencies import require_landlord_account
from app.features.landlord.schemas import (
    LandlordPostCreate,
    LandlordPostListOut,
    LandlordPostOut,
    LandlordPostUpdate,
    LandlordRoomListOut,
    LandlordRoomOut,
    LandlordRoomPayload,
    LandlordStatsOut,
)
from app.features.landlord.service import LandlordService
from app.features.users.models.account import Account

router = APIRouter()


async def _parse_room_form(request: Request) -> tuple[LandlordRoomPayload, list[object], bool]:
    try:
        form = await request.form()
    except (AssertionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="python-multipart is required to parse room form data",
        ) from exc

    payload_raw = form.get("payload")
    if not isinstance(payload_raw, str):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing payload")
    try:
        payload = LandlordRoomPayload.model_validate_json(payload_raw)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    publish_raw = form.get("publish", "false")
    publish = str(publish_raw).lower() not in {"false", "0", "no"}
    images = [value for key, value in form.multi_items() if key == "images" and hasattr(value, "file")]
    return payload, images, publish


@router.get("/rooms", response_model=LandlordRoomListOut)
def list_rooms(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordRoomListOut:
    return LandlordService(db).list_rooms(
        account,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
    )


@router.get("/rooms/{room_id}", response_model=LandlordRoomOut)
def get_room(
    room_id: int,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordRoomOut:
    return LandlordService(db).get_room(account, room_id)


@router.post("/rooms", response_model=LandlordRoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: Request,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordRoomOut:
    payload, images, publish = await _parse_room_form(request)
    return LandlordService(db).create_room(account, payload, images, publish=publish)


@router.put("/rooms/{room_id}", response_model=LandlordRoomOut)
async def update_room(
    room_id: int,
    request: Request,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordRoomOut:
    payload, images, _publish = await _parse_room_form(request)
    return LandlordService(db).update_room(account, room_id, payload, images)


@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    return LandlordService(db).delete_room(account, room_id)


@router.get("/stats", response_model=LandlordStatsOut)
def get_stats(
    range_filter: str = Query(default="30d", alias="range", pattern="^(7d|30d|3m)$"),
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordStatsOut:
    return LandlordService(db).get_stats(account, range_filter=range_filter)


@router.get("/posts", response_model=LandlordPostListOut)
def list_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    boosted_only: bool = Query(default=False, alias="boostedOnly"),
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordPostListOut:
    return LandlordService(db).list_posts(
        account,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        boosted_only=boosted_only,
    )


@router.post("/posts", response_model=LandlordPostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: LandlordPostCreate,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordPostOut:
    return LandlordService(db).create_post(account, payload)


@router.patch("/posts/{post_id}", response_model=LandlordPostOut)
def update_post(
    post_id: int,
    payload: LandlordPostUpdate,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> LandlordPostOut:
    return LandlordService(db).update_post(account, post_id, payload)


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    account: Account = Depends(require_landlord_account),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    return LandlordService(db).delete_post(account, post_id)
