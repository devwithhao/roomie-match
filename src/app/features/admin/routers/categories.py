from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.users.models.account import Account
from app.features.rooms.models.amenity import Amenity
from pydantic import BaseModel

router = APIRouter()

class CategoryCreate(BaseModel):
    tab: str
    name: str
    priceRange: str = "N/A"
    creator: str = "admin"
    quantity: int = 0
    icon: str = "tags"

@router.get("")
def list_categories(
    tab: str | None = Query(default=None),
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    if tab == "utility":
        amenities = db.query(Amenity).all()
        return {
            "items": [
                {
                    "id": f"CAT_UT{a.id:02d}",
                    "name": a.name,
                    "priceRange": "N/A",
                    "creator": "admin",
                    "quantity": 0,
                    "icon": a.icon_name if hasattr(a, "icon_name") else "check"
                } for a in amenities
            ]
        }
    elif tab == "area":
        return {
            "items": [
                { "id": 'CAT_A01', "name": 'TP. Hồ Chí Minh', "priceRange": '2.5M - 8M ₫', "creator": 'admin', "quantity": 486, "icon": 'map-pin' },
                { "id": 'CAT_A02', "name": 'Hà Nội', "priceRange": '2M - 7M ₫', "creator": 'admin', "quantity": 312, "icon": 'map-pin' },
            ]
        }
    elif tab == "roomType":
        return {
            "items": [
                { "id": 'CAT_RT01', "name": 'Phòng đơn', "priceRange": '1.5M - 4.5M ₫', "creator": 'admin', "quantity": 654, "icon": 'building' },
                { "id": 'CAT_RT02', "name": 'Căn hộ', "priceRange": '5M - 15M ₫', "creator": 'admin', "quantity": 320, "icon": 'building' },
            ]
        }
    return {"items": []}

@router.post("")
def create_category(
    payload: CategoryCreate,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    if payload.tab == "utility":
        amenity = Amenity(name=payload.name, icon_name=payload.icon)
        db.add(amenity)
        db.commit()
    return {"status": "success"}

@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    if category_id.startswith("CAT_UT"):
        actual_id = int(category_id.replace("CAT_UT", ""))
        amenity = db.query(Amenity).filter(Amenity.id == actual_id).first()
        if amenity:
            db.delete(amenity)
            db.commit()
    return {"status": "success"}
