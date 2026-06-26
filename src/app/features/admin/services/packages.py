from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.features.packages.models.package import Package
from app.features.packages.models.purchase import Purchase
from app.features.admin.schemas.packages import (
    AdminPackageOut,
    AdminPackageCreate,
    AdminPackageUpdate,
    AdminPackageStatusUpdate,
    AdminPackageListResponse,
)


class AdminPackageService:
    def __init__(self, db: Session):
        self.db = db

    def _map_to_dto(self, package: Package, total_purchased: int) -> AdminPackageOut:
        # Extract UI features list (display only)
        features_list: list[str] = []
        feature_quotas = {}

        if isinstance(package.features, dict):
            features_list = package.features.get("list", [])
            feature_quotas = {k: v for k, v in package.features.items() if k != "list"}
        elif isinstance(package.features, list):
            features_list = package.features

        # Include legacy columns into quotas to be seamless
        if getattr(package, "credits_match", None) is not None:
            feature_quotas["credits_match"] = package.credits_match
        if getattr(package, "credits_chatbot", None) is not None:
            feature_quotas["credits_chatbot"] = package.credits_chatbot

        icon = package.icon or "file-text"

        # Parse duration label
        duration = "Không giới hạn"
        if package.period:
            parts = package.period.split("_")
            if len(parts) >= 2 and parts[0].isdigit():
                if parts[1] == "days":
                    duration = f"{parts[0]} ngày"
                elif parts[1] == "months":
                    duration = f"{parts[0]} tháng"
                elif parts[1] == "years":
                    duration = f"{parts[0]} năm"
            else:
                duration = package.period

        return AdminPackageOut(
            id=f"PKG{package.id:03d}",
            name=package.name,
            icon=icon,
            target_role=package.target_role or "tenant",
            pricePerMonth=package.price_cents,
            duration=duration,
            features=features_list,
            feature_quotas=feature_quotas,
            totalPurchased=total_purchased,
            status="active" if package.active else "suspended",
            statusLabel="Đang bán" if package.active else "Tạm ngưng",
        )

    def get_purchases_count(self, package_id: int) -> int:
        return self.db.execute(
            select(func.count(Purchase.id)).where(Purchase.package_id == package_id, Purchase.status == "paid")
        ).scalar() or 0

    def list_packages(self) -> AdminPackageListResponse:
        packages = self.db.execute(select(Package)).scalars().all()
        items = [self._map_to_dto(pkg, self.get_purchases_count(pkg.id)) for pkg in packages]
        return AdminPackageListResponse(items=items, total=len(items))

    def get_package(self, package_id: int) -> AdminPackageOut:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
        return self._map_to_dto(package, self.get_purchases_count(package.id))

    def create_package(self, payload: AdminPackageCreate) -> AdminPackageOut:
        existing = self.db.execute(select(Package).where(Package.slug == payload.slug)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")

        # Build dynamic features dictionary for the JSON column
        features = payload.feature_quotas.copy() if payload.feature_quotas else {}
        features["list"] = payload.features_list

        package = Package(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            price_cents=payload.price_cents,
            currency=payload.currency,
            period=payload.period,
            active=payload.active,
            target_role=payload.target_role,
            icon=payload.icon,
            # Assign explicitly to backward compat columns if they are present
            credits_match=features.pop("credits_match", 0),
            credits_chatbot=features.pop("credits_chatbot", 0),
            features=features,
        )
        self.db.add(package)
        self.db.commit()
        return self._map_to_dto(package, 0)

    def update_package(self, package_id: int, payload: AdminPackageUpdate) -> AdminPackageOut:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")

        if payload.slug is not None and payload.slug != package.slug:
            existing = self.db.execute(select(Package).where(Package.slug == payload.slug)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")
            package.slug = payload.slug

        if payload.name is not None:
            package.name = payload.name
        if payload.description is not None:
            package.description = payload.description
        if payload.price_cents is not None:
            package.price_cents = payload.price_cents
        if payload.currency is not None:
            package.currency = payload.currency
        if payload.period is not None:
            package.period = payload.period
        if payload.active is not None:
            package.active = payload.active
        if payload.target_role is not None:
            package.target_role = payload.target_role
        if payload.icon is not None:
            package.icon = payload.icon

        current_features = package.features if isinstance(package.features, dict) else {}
        if isinstance(package.features, list):
            current_features = {"list": package.features}

        if payload.feature_quotas is not None:
            for k, v in payload.feature_quotas.items():
                if k == "credits_match":
                    package.credits_match = v
                elif k == "credits_chatbot":
                    package.credits_chatbot = v
                else:
                    current_features[k] = v
        
        if payload.features_list is not None:
            current_features["list"] = payload.features_list

        package.features = current_features

        self.db.commit()
        return self._map_to_dto(package, self.get_purchases_count(package.id))

    def update_package_status(self, package_id: int, payload: AdminPackageStatusUpdate) -> AdminPackageOut:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
        package.active = payload.active
        self.db.commit()
        return self._map_to_dto(package, self.get_purchases_count(package.id))

    def delete_package(self, package_id: int) -> dict:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")

        purchases_count = self.get_purchases_count(package_id)
        if purchases_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete package with active purchases. Please set active to false instead.",
            )

        self.db.delete(package)
        self.db.commit()
        return {"detail": "Package deleted successfully"}
