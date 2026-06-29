from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.users.models.account import Account
from pydantic import BaseModel

router = APIRouter()

class ComplaintStatusUpdate(BaseModel):
    status: str

@router.get("")
def list_complaints(
    status: str | None = Query(default=None),
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    return []

@router.patch("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: str,
    payload: ComplaintStatusUpdate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    return {"status": "success"}
