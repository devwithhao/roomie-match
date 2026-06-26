from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.features.packages.models.role_feature import RoleFeature
from app.features.admin.schemas.role_features import (
    RoleFeatureCreate,
    RoleFeatureUpdate,
    RoleFeatureOut,
    RoleFeatureListResponse,
)

class AdminRoleFeatureService:
    def __init__(self, db: Session):
        self.db = db

    def list_role_features(self, target_role: str = None) -> RoleFeatureListResponse:
        stmt = select(RoleFeature)
        if target_role:
            stmt = stmt.where(RoleFeature.target_role == target_role)
        features = self.db.execute(stmt.order_by(RoleFeature.id)).scalars().all()
        return RoleFeatureListResponse(items=features, total=len(features))

    def create_role_feature(self, payload: RoleFeatureCreate) -> RoleFeatureOut:
        existing = self.db.execute(
            select(RoleFeature).where(
                RoleFeature.target_role == payload.target_role,
                RoleFeature.feature_key == payload.feature_key
            )
        ).scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Feature key already exists for this role"
            )

        feature = RoleFeature(
            target_role=payload.target_role,
            feature_key=payload.feature_key,
            feature_name=payload.feature_name,
            description=payload.description,
            active=payload.active
        )
        self.db.add(feature)
        self.db.commit()
        return feature

    def update_role_feature(self, feature_id: int, payload: RoleFeatureUpdate) -> RoleFeatureOut:
        feature = self.db.execute(select(RoleFeature).where(RoleFeature.id == feature_id)).scalar_one_or_none()
        if not feature:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")

        # check duplicate key if changing target_role or feature_key
        new_role = payload.target_role if payload.target_role is not None else feature.target_role
        new_key = payload.feature_key if payload.feature_key is not None else feature.feature_key
        
        if (new_role != feature.target_role or new_key != feature.feature_key):
            existing = self.db.execute(
                select(RoleFeature).where(
                    RoleFeature.target_role == new_role,
                    RoleFeature.feature_key == new_key
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Feature key already exists for this role"
                )

        if payload.target_role is not None:
            feature.target_role = payload.target_role
        if payload.feature_key is not None:
            feature.feature_key = payload.feature_key
        if payload.feature_name is not None:
            feature.feature_name = payload.feature_name
        if payload.description is not None:
            feature.description = payload.description
        if payload.active is not None:
            feature.active = payload.active

        self.db.commit()
        return feature

    def delete_role_feature(self, feature_id: int) -> dict:
        feature = self.db.execute(select(RoleFeature).where(RoleFeature.id == feature_id)).scalar_one_or_none()
        if not feature:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")

        self.db.delete(feature)
        self.db.commit()
        return {"detail": "Feature deleted successfully"}
