from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.features.packages.models import Package, Purchase, Entitlement
from app.features.packages.repositories import (
    PackageRepository,
    PurchaseRepository,
    EntitlementRepository,
)


class PackageService:
    """Service for package-related operations"""

    def __init__(self, db: Session):
        self.db = db
        self.package_repo = PackageRepository(db)
        self.purchase_repo = PurchaseRepository(db)
        self.entitlement_repo = EntitlementRepository(db)

    def get_all_packages(self) -> list[Package]:
        """Get all active packages"""
        return self.package_repo.get_all_active()

    def initiate_purchase(
        self, account_id: int, package_id: int, provider: str = "stripe"
    ) -> Purchase:
        """Initiate a new purchase (mark as pending, waiting for webhook confirmation)"""
        package = self.package_repo.get_by_id(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")

        purchase = Purchase(
            account_id=account_id,
            package_id=package_id,
            provider=provider,
            amount_cents=package.price_cents,
            currency=package.currency,
            status="pending",  # waiting for webhook
        )
        return self.purchase_repo.create(purchase)

    def confirm_purchase(
        self, purchase_id: int, provider_payment_id: str, raw_payload: dict = None
    ) -> tuple[Purchase, list[Entitlement]]:
        """Confirm purchase (from webhook) and grant entitlements"""
        purchase = self.purchase_repo.get_by_id(purchase_id)
        if not purchase:
            raise ValueError(f"Purchase {purchase_id} not found")

        # Update purchase status
        purchase.status = "paid"
        purchase.provider_payment_id = provider_payment_id
        purchase.raw_payload = raw_payload
        self.db.flush()

        # Grant entitlements from package
        package = self.package_repo.get_by_id(purchase.package_id)
        if not package:
            raise ValueError(f"Package {purchase.package_id} not found")

        entitlements = []

        if package.credits_match:
            ent = Entitlement(
                account_id=purchase.account_id,
                feature_key="match",
                quantity=package.credits_match,
                source_purchase_id=purchase.id,
            )
            entitlements.append(self.entitlement_repo.create(ent))

        if package.credits_chatbot:
            ent = Entitlement(
                account_id=purchase.account_id,
                feature_key="chatbot",
                quantity=package.credits_chatbot,
                source_purchase_id=purchase.id,
            )
            entitlements.append(self.entitlement_repo.create(ent))

        if package.period:
            # Add time-based entitlements if period is defined
            if package.period == "30_days":
                expires_at = datetime.utcnow() + timedelta(days=30)
            elif package.period == "annual":
                expires_at = datetime.utcnow() + timedelta(days=365)
            else:
                expires_at = None

            if expires_at:
                ent = Entitlement(
                    account_id=purchase.account_id,
                    feature_key="active_subscription",
                    quantity=None,  # unlimited
                    expires_at=expires_at,
                    source_purchase_id=purchase.id,
                )
                entitlements.append(self.entitlement_repo.create(ent))

        return purchase, entitlements

    def get_account_purchases(self, account_id: int) -> list[Purchase]:
        """Get all purchases for an account"""
        return self.purchase_repo.get_by_account_id(account_id)

    def get_account_entitlements(self, account_id: int) -> list[Entitlement]:
        """Get all entitlements for an account"""
        return self.entitlement_repo.get_by_account_id(account_id)

    def check_entitlement(self, account_id: int, feature_key: str) -> bool:
        """Check if account has active entitlement for feature"""
        entitlement = self.entitlement_repo.get_by_account_and_feature(
            account_id, feature_key
        )
        if not entitlement:
            return False
        if entitlement.expires_at and entitlement.expires_at < datetime.utcnow():
            return False  # expired
        return True

    def consume_credit(
        self, account_id: int, feature_key: str, amount: int = 1
    ) -> bool:
        """Consume credit from entitlement (returns True if successful)"""
        entitlement = self.entitlement_repo.get_by_account_and_feature(
            account_id, feature_key
        )
        if not entitlement:
            return False

        if entitlement.quantity is None:
            return True  # unlimited

        if entitlement.quantity < amount:
            return False  # not enough credits

        self.entitlement_repo.update_quantity(
            entitlement.id, entitlement.quantity - amount
        )
        return True
