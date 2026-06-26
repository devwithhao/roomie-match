from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.features.admin.schemas.role_features import (
    RoleFeatureCreate,
    RoleFeatureUpdate,
    RoleFeatureOut,
    RoleFeatureListResponse,
)
from app.features.admin.services.role_features import AdminRoleFeatureService

router = APIRouter()

def get_role_feature_service(db: Session = Depends(get_db)) -> AdminRoleFeatureService:
    return AdminRoleFeatureService(db)

@router.get("/", response_model=RoleFeatureListResponse)
def list_role_features(
    target_role: Optional[str] = None,
    service: AdminRoleFeatureService = Depends(get_role_feature_service)
):
    return service.list_role_features(target_role=target_role)

@router.post("/", response_model=RoleFeatureOut)
def create_role_feature(
    payload: RoleFeatureCreate,
    service: AdminRoleFeatureService = Depends(get_role_feature_service)
):
    return service.create_role_feature(payload)

@router.put("/{feature_id}", response_model=RoleFeatureOut)
def update_role_feature(
    feature_id: int,
    payload: RoleFeatureUpdate,
    service: AdminRoleFeatureService = Depends(get_role_feature_service)
):
    return service.update_role_feature(feature_id, payload)

@router.delete("/{feature_id}")
def delete_role_feature(
    feature_id: int,
    service: AdminRoleFeatureService = Depends(get_role_feature_service)
):
    return service.delete_role_feature(feature_id)
