from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.users.models.account import Account
from app.features.admin.schemas.packages import (
    AdminPackageCreate,
    AdminPackageListResponse,
    AdminPackageOut,
    AdminPackageUpdate,
    AdminPackageStatusUpdate,
)
from app.features.admin.services.packages import AdminPackageService

router = APIRouter()

@router.get("", response_model=AdminPackageListResponse)
def list_packages(
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminPackageListResponse:
    return AdminPackageService(db).list_packages()

@router.get("/{package_id}", response_model=AdminPackageOut)
def get_package(
    package_id: int,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminPackageOut:
    return AdminPackageService(db).get_package(package_id)

@router.post("", response_model=AdminPackageOut, status_code=status.HTTP_201_CREATED)
def create_package(
    payload: AdminPackageCreate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminPackageOut:
    return AdminPackageService(db).create_package(payload)

@router.put("/{package_id}", response_model=AdminPackageOut)
def update_package(
    package_id: int,
    payload: AdminPackageUpdate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminPackageOut:
    return AdminPackageService(db).update_package(package_id, payload)

@router.patch("/{package_id}/status", response_model=AdminPackageOut)
def update_package_status(
    package_id: int,
    payload: AdminPackageStatusUpdate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> AdminPackageOut:
    return AdminPackageService(db).update_package_status(package_id, payload)

@router.delete("/{package_id}", status_code=status.HTTP_200_OK)
def delete_package(
    package_id: int,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
) -> dict:
    return AdminPackageService(db).delete_package(package_id)
