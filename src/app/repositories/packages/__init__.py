from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.packages import Package, Purchase, Entitlement


class PackageRepository:
    """Repository for Package queries"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, package_id: int) -> Package | None:
        """Get package by ID"""
        return self.db.execute(
            select(Package).where(Package.id == package_id)
        ).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Package | None:
        """Get package by slug"""
        return self.db.execute(
            select(Package).where(Package.slug == slug)
        ).scalar_one_or_none()

    def get_all_active(self) -> list[Package]:
        """Get all active packages"""
        return (
            self.db.execute(select(Package).where(Package.active == True))
            .scalars()
            .all()
        )

    def get_all(self) -> list[Package]:
        """Get all packages"""
        return self.db.execute(select(Package)).scalars().all()


class PurchaseRepository:
    """Repository for Purchase queries"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, purchase: Purchase) -> Purchase:
        """Create a purchase record"""
        self.db.add(purchase)
        self.db.flush()
        return purchase

    def get_by_id(self, purchase_id: int) -> Purchase | None:
        """Get purchase by ID"""
        return self.db.execute(
            select(Purchase).where(Purchase.id == purchase_id)
        ).scalar_one_or_none()

    def get_by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> Purchase | None:
        """Get purchase by provider + payment ID (for idempotency)"""
        return self.db.execute(
            select(Purchase).where(
                and_(
                    Purchase.provider == provider,
                    Purchase.provider_payment_id == provider_payment_id,
                )
            )
        ).scalar_one_or_none()

    def get_by_account_id(self, account_id: int) -> list[Purchase]:
        """Get all purchases for an account"""
        return (
            self.db.execute(
                select(Purchase)
                .where(Purchase.account_id == account_id)
                .order_by(Purchase.created_at.desc())
            )
            .scalars()
            .all()
        )

    def update_status(
        self, purchase_id: int, status: str, raw_payload: dict = None
    ) -> Purchase | None:
        """Update purchase status"""
        purchase = self.get_by_id(purchase_id)
        if purchase:
            purchase.status = status
            if raw_payload:
                purchase.raw_payload = raw_payload
            self.db.flush()
        return purchase


class EntitlementRepository:
    """Repository for Entitlement queries"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, entitlement: Entitlement) -> Entitlement:
        """Create an entitlement"""
        self.db.add(entitlement)
        self.db.flush()
        return entitlement

    def get_by_id(self, entitlement_id: int) -> Entitlement | None:
        """Get entitlement by ID"""
        return self.db.execute(
            select(Entitlement).where(Entitlement.id == entitlement_id)
        ).scalar_one_or_none()

    def get_by_account_and_feature(
        self, account_id: int, feature_key: str
    ) -> Entitlement | None:
        """Get active entitlement for account + feature"""
        return self.db.execute(
            select(Entitlement).where(
                and_(
                    Entitlement.account_id == account_id,
                    Entitlement.feature_key == feature_key,
                )
            )
        ).scalar_one_or_none()

    def get_by_account_id(self, account_id: int) -> list[Entitlement]:
        """Get all entitlements for an account"""
        return (
            self.db.execute(
                select(Entitlement)
                .where(Entitlement.account_id == account_id)
                .order_by(Entitlement.created_at.desc())
            )
            .scalars()
            .all()
        )

    def update_quantity(
        self, entitlement_id: int, new_quantity: int
    ) -> Entitlement | None:
        """Update entitlement quantity (decrement for consumption)"""
        entitlement = self.get_by_id(entitlement_id)
        if entitlement and entitlement.quantity is not None:
            entitlement.quantity = max(0, new_quantity)  # don't go negative
            self.db.flush()
        return entitlement
