from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.admin.schemas.moderation import PostModerationUpdate, RoomModerationUpdate, VerificationModerationUpdate
from app.features.admin.services.moderation import AdminModerationService
from app.features.users.models.account import Account

router = APIRouter()


@router.get("/posts")
def list_posts(status: str | None = Query(default=None), _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).list_posts(status)


@router.patch("/posts/{post_id}/status")
def moderate_post(post_id: int, payload: PostModerationUpdate, admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).moderate_post(admin, post_id, payload)


@router.delete("/posts/{post_id}")
def close_post(post_id: int, admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).moderate_post(admin, post_id, PostModerationUpdate(status="closed"))


@router.get("/rooms")
def list_rooms(status: str | None = Query(default=None), _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).list_rooms(status)


@router.patch("/rooms/{room_id}/status")
def moderate_room(room_id: int, payload: RoomModerationUpdate, _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).moderate_room(room_id, payload)


@router.get("/landlord-verifications")
def list_verifications(status: str | None = Query(default=None), _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).list_verifications(status)


@router.patch("/landlord-verifications/{verification_id}")
def moderate_verification(verification_id: int, payload: VerificationModerationUpdate, admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).moderate_verification(admin, verification_id, payload)


@router.get("/landlord-verifications/{verification_id}/images/{side}")
def get_verification_image(verification_id: int, side: str, _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    if side not in {"front", "back"}:
        raise HTTPException(status_code=404, detail="Image not found")
    return AdminModerationService(db).verification_image_path(verification_id, side)


@router.get("/orders")
def list_orders(_admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).list_purchases()


@router.patch("/orders/{purchase_id}/status")
def update_order_status(purchase_id: int, payload: dict, _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).update_purchase_status(purchase_id, str(payload.get("status", "")))


@router.delete("/orders/{purchase_id}")
def delete_order(purchase_id: int, _admin: Account = Depends(require_admin_account), db: Session = Depends(get_db)):
    return AdminModerationService(db).delete_purchase(purchase_id)
