from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.features.packages.models import Entitlement, Package, PackageUsageEvent, Purchase
from app.features.packages.repositories import (
    EntitlementRepository,
    PackageRepository,
    PackageUsageEventRepository,
    PurchaseRepository,
)


class PackageService:
    """Service for package-related operations"""

    def __init__(self, db: Session):
        self.db = db
        self.package_repo = PackageRepository(db)
        self.purchase_repo = PurchaseRepository(db)
        self.entitlement_repo = EntitlementRepository(db)
        self.usage_event_repo = PackageUsageEventRepository(db)

    def get_all_packages(self, target_role: str | None = None) -> list[Package]:
        """Get all active packages"""
        return self.package_repo.get_all_active(target_role=target_role)

    def initiate_purchase(
        self,
        account_id: int,
        package_id: int,
        provider: str = "stripe",
        account_role: str | None = None,
    ) -> Purchase:
        """Create a purchase and mark it paid in dev until a real payment gateway exists."""
        package = self.package_repo.get_by_id(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        if account_role and package.target_role not in {account_role, "all"}:
            raise PermissionError("Package is not available for this account role")

        purchase = Purchase(
            account_id=account_id,
            package_id=package_id,
            provider=provider,
            amount_cents=package.price_cents,
            currency=package.currency,
            status="paid",
        )
        created = self.purchase_repo.create(purchase)
        created.provider_payment_id = f"dev-{created.id}"
        self._grant_entitlements(created, package)
        return created

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

        return purchase, self._grant_entitlements(purchase, package)

    def _grant_entitlements(self, purchase: Purchase, package: Package) -> list[Entitlement]:
        expires_at = None
        if package.period == "30_days":
            expires_at = datetime.utcnow() + timedelta(days=30)
        elif package.period == "annual":
            expires_at = datetime.utcnow() + timedelta(days=365)

        entitlements = []
        if package.credits_match:
            entitlements.append(
                self.entitlement_repo.create(
                    Entitlement(
                        account_id=purchase.account_id,
                        feature_key="match",
                        quantity=package.credits_match,
                        expires_at=expires_at,
                        source_purchase_id=purchase.id,
                    )
                )
            )

        if package.credits_chatbot:
            entitlements.append(
                self.entitlement_repo.create(
                    Entitlement(
                        account_id=purchase.account_id,
                        feature_key="chatbot",
                        quantity=package.credits_chatbot,
                        expires_at=expires_at,
                        source_purchase_id=purchase.id,
                    )
                )
            )

        features = package.features if isinstance(package.features, dict) else {}
        for feature_key in ("posts_limit", "photo_limit", "boost_limit"):
            quantity = features.get(feature_key)
            if isinstance(quantity, int):
                entitlements.append(
                    self.entitlement_repo.create(
                        Entitlement(
                            account_id=purchase.account_id,
                            feature_key=feature_key,
                            quantity=quantity,
                            expires_at=expires_at,
                            source_purchase_id=purchase.id,
                        )
                    )
                )

        if expires_at:
            entitlements.append(
                self.entitlement_repo.create(
                    Entitlement(
                        account_id=purchase.account_id,
                        feature_key="active_subscription",
                        quantity=None,
                        expires_at=expires_at,
                        source_purchase_id=purchase.id,
                    )
                )
            )

        return entitlements

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

    def has_credit(self, account_id: int, feature_key: str, amount: int = 1) -> bool:
        if amount <= 0:
            return True
        quantity = self.entitlement_repo.get_available_quantity(account_id, feature_key)
        return quantity is None or quantity >= amount

    def ensure_credit(self, account_id: int, feature_key: str, amount: int = 1) -> None:
        if not self.has_credit(account_id, feature_key, amount):
            raise ValueError("insufficient_credit")

    def consume_credit(
        self, account_id: int, feature_key: str, amount: int = 1
    ) -> bool:
        """Consume credit from entitlement (returns True if successful)"""
        entitlement = self.entitlement_repo.get_consumable_by_account_and_feature(
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

    def consume_credit_with_event(
        self,
        account_id: int,
        feature_key: str,
        amount: int = 1,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        metadata: dict | None = None,
    ) -> bool:
        if amount <= 0:
            return True

        entitlement = self.entitlement_repo.get_consumable_by_account_and_feature(
            account_id, feature_key
        )
        if not entitlement:
            return False
        if entitlement.quantity is not None and entitlement.quantity < amount:
            return False

        if entitlement.quantity is not None:
            self.entitlement_repo.update_quantity(entitlement.id, entitlement.quantity - amount)

        self.usage_event_repo.create(
            PackageUsageEvent(
                account_id=account_id,
                feature_key=feature_key,
                amount=amount,
                entity_type=entity_type,
                entity_id=entity_id,
                source_purchase_id=entitlement.source_purchase_id,
                metadata_json=metadata,
            )
        )
        return True
