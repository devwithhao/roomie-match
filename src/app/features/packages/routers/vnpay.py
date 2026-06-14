from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.features.users.dependencies import get_current_account
from app.database.session import get_db
from app.features.users.models import Account
from app.features.packages.schemas import PurchaseCreate
from app.features.packages.service import PackageService
from app.features.packages.vnpay_service import VNPAYService

router = APIRouter()

@router.post("/create_url", status_code=status.HTTP_200_OK)
def create_vnpay_payment_url(
    payload: PurchaseCreate,
    request: Request,
    current_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    service = PackageService(db)
    try:
        purchase = service.initiate_purchase(current_account.id, payload.package_id, provider="vnpay")
        db.commit()
        
        ip_addr = request.client.host
        
        order_desc = f"Thanh toan don hang {purchase.id} - Ghi co tai khoan {current_account.email}"
        payment_url = VNPAYService.create_payment_url(
            order_id=str(purchase.id),
            amount_cents=purchase.amount_cents,
            order_desc=order_desc,
            ip_addr=ip_addr
        )
        
        return {"payment_url": payment_url, "purchase_id": purchase.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/ipn")
def vnpay_ipn(request: Request, db: Session = Depends(get_db)):
    """
    VNPAY IPN webhook endpoint
    """
    query_params = dict(request.query_params)
    
    if not VNPAYService.verify_payment(query_params):
        return {"RspCode": "97", "Message": "Invalid Checksum"}
        
    order_id_str = query_params.get("vnp_TxnRef")
    response_code = query_params.get("vnp_ResponseCode")
    transaction_no = query_params.get("vnp_TransactionNo")
    
    if not order_id_str:
        return {"RspCode": "99", "Message": "Missing TxnRef"}
        
    try:
        order_id = int(order_id_str)
    except ValueError:
        return {"RspCode": "01", "Message": "Order not found"}
        
    service = PackageService(db)
    purchase = service.purchase_repo.get_by_id(order_id)
    
    if not purchase:
        return {"RspCode": "01", "Message": "Order not found"}
        
    if purchase.status == "paid":
        return {"RspCode": "02", "Message": "Order already confirmed"}
        
    vnp_amount = int(query_params.get("vnp_Amount", 0))
    expected_amount = purchase.amount_cents * 100
    if vnp_amount != expected_amount:
        return {"RspCode": "04", "Message": "Invalid amount"}
        
    if response_code == "00":
        # Success
        try:
            service.confirm_purchase(purchase.id, provider_payment_id=transaction_no, raw_payload=query_params)
            db.commit()
            return {"RspCode": "00", "Message": "Confirm Success"}
        except Exception as e:
            db.rollback()
            return {"RspCode": "99", "Message": f"Server error: {str(e)}"}
    else:
        # Failed
        service.purchase_repo.update_status(purchase.id, status="failed", raw_payload=query_params)
        db.commit()
        return {"RspCode": "00", "Message": "Confirm Success"}
