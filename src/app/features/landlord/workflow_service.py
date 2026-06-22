from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.landlord.image_uploader import local_public_path, upload_verification_image
from app.features.landlord.models import LandlordVerification, Notification
from app.features.landlord.schemas import LandlordVerificationOut, NotificationListOut, NotificationOut
from app.features.users.models.account import Account


class LandlordWorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_verification(self, account: Account) -> LandlordVerificationOut | None:
        row = self.db.scalar(select(LandlordVerification).where(LandlordVerification.account_id == account.id))
        return self._verification_out(row) if row else None

    def get_private_image(self, account: Account, side: str):
        row = self.db.scalar(select(LandlordVerification).where(LandlordVerification.account_id == account.id))
        if row is None:
            raise HTTPException(status_code=404, detail="Verification not found")
        return self.verification_image_response(row.front_image_url if side == "front" else row.back_image_url)

    def submit_verification(
        self,
        account: Account,
        *,
        legal_name: str,
        identity_number: str,
        issued_date: date,
        issued_place: str,
        front_file,
        back_file,
    ) -> LandlordVerificationOut:
        for file in (front_file, back_file):
            if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                raise HTTPException(status_code=422, detail="CCCD chỉ chấp nhận JPG, PNG hoặc WEBP")
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
            if size > 5 * 1024 * 1024:
                raise HTTPException(status_code=422, detail="Mỗi ảnh CCCD không được vượt quá 5MB")

        front_url = self._save_private_image(front_file, account.id, "front")
        back_url = self._save_private_image(back_file, account.id, "back")
        row = self.db.scalar(select(LandlordVerification).where(LandlordVerification.account_id == account.id))
        if row is None:
            row = LandlordVerification(account_id=account.id, legal_name=legal_name, identity_number=identity_number, issued_date=issued_date, issued_place=issued_place, front_image_url=front_url, back_image_url=back_url)
            self.db.add(row)
        else:
            if row.status == "approved":
                raise HTTPException(status_code=409, detail="Hồ sơ đã được xác minh")
            row.legal_name = legal_name
            row.identity_number = identity_number
            row.issued_date = issued_date
            row.issued_place = issued_place
            row.front_image_url = front_url
            row.back_image_url = back_url
            row.status = "pending"
            row.rejection_reason = None
            row.reviewed_by = None
            row.reviewed_at = None
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Số CCCD đã được sử dụng") from exc
        self.db.refresh(row)
        return self._verification_out(row)

    def list_notifications(self, account: Account, limit: int, offset: int) -> NotificationListOut:
        where = Notification.account_id == account.id
        total = int(self.db.scalar(select(func.count()).select_from(Notification).where(where)) or 0)
        unread = int(self.db.scalar(select(func.count()).select_from(Notification).where(where, Notification.read_at.is_(None))) or 0)
        rows = self.db.scalars(select(Notification).where(where).order_by(Notification.created_at.desc()).offset(offset).limit(limit)).all()
        return NotificationListOut(items=[self._notification_out(row) for row in rows], total=total, unread=unread)

    def mark_notification_read(self, account: Account, notification_id: int) -> NotificationOut:
        row = self.db.scalar(select(Notification).where(Notification.id == notification_id, Notification.account_id == account.id))
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
        row.read_at = row.read_at or datetime.utcnow()
        self.db.commit()
        return self._notification_out(row)

    @staticmethod
    def _notification_out(row: Notification) -> NotificationOut:
        return NotificationOut(id=row.id, type=row.type, title=row.title, message=row.message, entity_type=row.entity_type, entity_id=row.entity_id, read=row.read_at is not None, created_at=row.created_at)

    @staticmethod
    def _save_private_image(upload, account_id: int, side: str) -> str:
        base_name = f"{account_id}-{side}-{Path(upload.filename or '').name}"
        return upload_verification_image(upload.file, filename=base_name)

    @staticmethod
    def private_image_path(filename: str) -> Path:
        target = local_public_path(filename)
        if target is None or not target.is_file():
            raise HTTPException(status_code=404, detail="Verification image not found")
        return target

    @classmethod
    def verification_image_response(cls, image_ref: str):
        local_path = cls.private_image_path(image_ref) if image_ref.startswith(settings.public_storage_url.rstrip("/")) else None
        if local_path is not None:
            return FileResponse(local_path)
        return RedirectResponse(image_ref)

    @staticmethod
    def _verification_out(row: LandlordVerification) -> LandlordVerificationOut:
        return LandlordVerificationOut(
            id=row.id, legal_name=row.legal_name, identity_number=row.identity_number,
            issued_date=row.issued_date, issued_place=row.issued_place,
            front_image_url="/api/v1/landlord/verification/images/front",
            back_image_url="/api/v1/landlord/verification/images/back",
            status=row.status, rejection_reason=row.rejection_reason,
            created_at=row.created_at, updated_at=row.updated_at,
        )
