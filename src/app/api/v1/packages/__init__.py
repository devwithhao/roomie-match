from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.deps import get_current_account
from app.database.session import get_db
from app.models.users import Account
from app.schemas.packages import PackageOut, PurchaseOut, EntitlementOut, PurchaseCreate
from app.services.packages import PackageService

router = APIRouter()


@router.get("/", response_model=list[PackageOut])
def list_packages(db: Session = Depends(get_db)):
    service = PackageService(db)
    packages = service.get_all_packages()
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
        purchase = service.initiate_purchase(current_account.id, payload.package_id)
        db.commit()
        return purchase
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
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
