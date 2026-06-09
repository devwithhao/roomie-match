from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.packages.service import PackageService
import json

router = APIRouter()


@router.post("/webhook")
async def package_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="empty payload")
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid JSON payload: {e}")
    provider = payload.get("provider")
    provider_payment_id = payload.get("provider_payment_id")
    purchase_id = payload.get("purchase_id")

    service = PackageService(db)

    # Find purchase
    purchase = None
    if provider and provider_payment_id:
        purchase = service.purchase_repo.get_by_provider_payment_id(
            provider, provider_payment_id
        )
    elif purchase_id:
        purchase = service.purchase_repo.get_by_id(purchase_id)

    if not purchase:
        raise HTTPException(status_code=404, detail="purchase not found")

    if purchase.status == "paid":
        return {"status": "already_paid", "purchase_id": purchase.id}

    try:
        confirmed_purchase, entitlements = service.confirm_purchase(
            purchase.id, provider_payment_id, raw_payload=payload
        )
        db.commit()
        return {"status": "ok", "purchase_id": confirmed_purchase.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
