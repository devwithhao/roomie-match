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
        if isinstance(package.features, list):
            features_list = package.features
        elif isinstance(package.features, dict):
            features_list = package.features.get("list", [])

        # Extract landlord quotas from features dict
        posts_limit = 0
        photo_limit = 0
        boost_limit = 0
        if isinstance(package.features, dict):
            posts_limit = package.features.get("posts_limit", 0)
            photo_limit = package.features.get("photo_limit", 0)
            boost_limit = package.features.get("boost_limit", 0)

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
            credits_match=package.credits_match or 0,
            credits_chatbot=package.credits_chatbot or 0,
            posts_limit=posts_limit,
            photo_limit=photo_limit,
            boost_limit=boost_limit,
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

        # Build features theo target_role:
        # - landlord: dict với quota keys để _grant_entitlements đọc
        # - tenant/all:  list để hiển thị UI (credits cấp qua credits_match/credits_chatbot)
        if payload.target_role == "landlord":
            features: list | dict = {
                "posts_limit": payload.posts_limit,
                "photo_limit": payload.photo_limit,
                "boost_limit": payload.boost_limit,
            }
        else:
            features = payload.features_list

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
            credits_match=payload.credits_match,
            credits_chatbot=payload.credits_chatbot,
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
        if payload.credits_match is not None:
            package.credits_match = payload.credits_match
        if payload.credits_chatbot is not None:
            package.credits_chatbot = payload.credits_chatbot

        # Cập nhật features: nếu gói landlord và có quota mới → rebuild dict
        effective_role = payload.target_role or package.target_role
        quota_changed = any(v is not None for v in [payload.posts_limit, payload.photo_limit, payload.boost_limit])
        if effective_role == "landlord" and quota_changed:
            current = package.features if isinstance(package.features, dict) else {}
            package.features = {
                "posts_limit": payload.posts_limit if payload.posts_limit is not None else current.get("posts_limit", 0),
                "photo_limit": payload.photo_limit if payload.photo_limit is not None else current.get("photo_limit", 0),
                "boost_limit": payload.boost_limit if payload.boost_limit is not None else current.get("boost_limit", 0),
            }
        elif payload.features_list is not None:
            package.features = payload.features_list

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
