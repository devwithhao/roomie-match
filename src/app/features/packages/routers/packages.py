from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.features.users.dependencies import get_current_account
from app.database.session import get_db
from app.features.users.models import Account
from app.features.users.models.role import Role
from app.features.users.role_utils import canonical_account_type
from app.features.packages.schemas import PackageOut, PurchaseOut, EntitlementOut, PurchaseCreate
from app.features.packages.service import PackageService

router = APIRouter()


@router.get("/", response_model=list[PackageOut])
def list_packages(
    target_role: str | None = Query(default=None, pattern="^(tenant|landlord|all)$"),
    db: Session = Depends(get_db),
):
    service = PackageService(db)
    packages = service.get_all_packages(target_role=target_role)
    return packages


@router.post(
    "/purchase", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED
)
def create_purchase(
    payload: PurchaseCreate,
    current_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    service = PackageService(db)
    try:
        role = db.get(Role, current_account.role_id)
        account_role = canonical_account_type(role.name, role.description) if role else None
        purchase = service.initiate_purchase(
            current_account.id,
            payload.package_id,
            account_role=account_role,
        )
        db.commit()
        return purchase
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me/purchases", response_model=list[PurchaseOut])
def list_my_purchases(
    current_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    service = PackageService(db)
    purchases = service.get_account_purchases(current_account.id)
    return purchases


@router.get("/me/entitlements", response_model=list[EntitlementOut])
def list_my_entitlements(
    current_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    service = PackageService(db)
    entitlements = service.get_account_entitlements(current_account.id)
    return entitlements
