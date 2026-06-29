from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.users.models.account import Account
from app.features.packages.models.purchase import Purchase
from app.features.packages.models.package import Package
from pydantic import BaseModel

router = APIRouter()

class OrderStatusUpdate(BaseModel):
    status: str

@router.get("")
def list_orders(
    status: str | None = Query(default=None),
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    query = db.query(Purchase, Account, Package).join(Account, Purchase.account_id == Account.id).join(Package, Purchase.package_id == Package.id)
    if status:
        db_status = "paid" if status == "success" else status
        query = query.filter(Purchase.status == db_status)
        
    purchases = query.order_by(desc(Purchase.created_at)).all()
    
    results = []
    for purchase, account, package in purchases:
        results.append({
            "id": f"ORD{purchase.id:03d}",
            "username": account.username,
            "email": account.email,
            "packageName": package.name,
            "price": purchase.amount_cents,
            "status": "success" if purchase.status == "paid" else purchase.status,
            "date": purchase.created_at.strftime("%d/%m/%Y") if purchase.created_at else ""
        })
        
    return results

@router.patch("/{order_id}/status")
def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    actual_id = int(order_id.replace("ORD", ""))
    purchase = db.query(Purchase).filter(Purchase.id == actual_id).first()
    if purchase:
        purchase.status = "paid" if payload.status == "success" else payload.status
        db.commit()
    return {"status": "success"}

@router.delete("/{order_id}")
def delete_order(
    order_id: str,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    actual_id = int(order_id.replace("ORD", ""))
    purchase = db.query(Purchase).filter(Purchase.id == actual_id).first()
    if purchase:
        db.delete(purchase)
        db.commit()
    return {"status": "success"}
