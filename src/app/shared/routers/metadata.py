from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.rooms.models.amenity import Amenity
from app.features.rooms.models.room_type import RoomType
from pydantic import BaseModel

router = APIRouter()

class CategoryItem(BaseModel):
    id: str
    name: str
    icon: str

class CategoriesResponse(BaseModel):
    room_types: list[CategoryItem]
    amenities: list[CategoryItem]

@router.get("/categories", response_model=CategoriesResponse)
def get_categories(db: Session = Depends(get_db)):
    room_types = db.query(RoomType).all()
    amenities = db.query(Amenity).all()

    return CategoriesResponse(
        room_types=[
            CategoryItem(
                id=f"CAT_RT{rt.id:02d}",
                name=rt.name,
                icon=rt.icon_name if rt.icon_name else "building"
            ) for rt in room_types
        ],
        amenities=[
            CategoryItem(
                id=f"CAT_UT{a.id:02d}",
                name=a.name,
                icon=a.icon_name if a.icon_name else "check"
            ) for a in amenities
        ]
    )
