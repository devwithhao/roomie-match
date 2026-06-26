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
        # Backward compatibility for old features format
        features_list = package.features
        icon = package.icon
        target_customer = package.target_customer

        if isinstance(package.features, dict):
            features_list = package.features.get("list", [])
            icon = icon or package.features.get("icon", "file-text")
            target_customer = target_customer or package.features.get("targetCustomer", "owner")
            
        icon = icon or "file-text"
        target_customer = target_customer or "owner"
        target_customer_label = "Chủ trọ" if target_customer == "owner" else "Người thuê"
        
        # Parse duration
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

        if not isinstance(features_list, list):
            features_list = []

        return AdminPackageOut(
            id=f"PKG{package.id:03d}",
            name=package.name,
            icon=icon,
            targetCustomer=target_customer,
            targetCustomerLabel=target_customer_label,
            pricePerMonth=package.price_cents,
            duration=duration,
            features=features_list,
            totalPurchased=total_purchased,
            status="active" if package.active else "suspended",
            statusLabel="Đang bán" if package.active else "Tạm ngưng"
        )

    def get_purchases_count(self, package_id: int) -> int:
        return self.db.execute(
            select(func.count(Purchase.id)).where(Purchase.package_id == package_id, Purchase.status == 'paid')
        ).scalar() or 0

    def list_packages(self) -> AdminPackageListResponse:
        packages = self.db.execute(select(Package)).scalars().all()
        
        items = []
        for pkg in packages:
            count = self.get_purchases_count(pkg.id)
            items.append(self._map_to_dto(pkg, count))
            
        return AdminPackageListResponse(items=items, total=len(items))

    def get_package(self, package_id: int) -> AdminPackageOut:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
        
        count = self.get_purchases_count(package.id)
        return self._map_to_dto(package, count)

    def create_package(self, payload: AdminPackageCreate) -> AdminPackageOut:
        existing = self.db.execute(select(Package).where(Package.slug == payload.slug)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")

        features_list = payload.features_list if payload.features_list is not None else []

        package = Package(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            price_cents=payload.price_cents,
            currency=payload.currency,
            period=payload.period,
            active=payload.active,
            icon=payload.icon,
            target_customer=payload.targetCustomer,
            features=features_list
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
            
        if payload.icon is not None:
            package.icon = payload.icon
        if payload.targetCustomer is not None:
            package.target_customer = payload.targetCustomer
        
        # Backward compatibility check for features
        if payload.features_list is not None:
            package.features = payload.features_list
        elif isinstance(package.features, dict) and "list" in package.features:
            # If it's old format and we're not updating features_list, extract it to new format
            package.features = package.features["list"]
        self.db.commit()
        
        count = self.get_purchases_count(package.id)
        return self._map_to_dto(package, count)

    def update_package_status(self, package_id: int, payload: AdminPackageStatusUpdate) -> AdminPackageOut:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
            
        package.active = payload.active
        self.db.commit()
        
        count = self.get_purchases_count(package.id)
        return self._map_to_dto(package, count)

    def delete_package(self, package_id: int) -> dict:
        package = self.db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
            
        # Check if there are any purchases
        purchases_count = self.get_purchases_count(package_id)
        if purchases_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot delete package with active purchases. Please set active to false instead."
            )

        self.db.delete(package)
        self.db.commit()
        
        return {"detail": "Package deleted successfully"}
