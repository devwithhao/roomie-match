import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.rooms.models.room import Room
from app.features.rooms.models.post import Post
from app.features.rooms.models.room_image import RoomImage


class RoomSearchInput(BaseModel):
    district: Optional[str] = Field(
        default="",
        description="One district name only, for example 'Binh Thanh' or 'Thu Duc'.",
    )
    max_price: Optional[str] = Field(
        default="",
        description="Maximum budget in VND, for example '4000000' or '5000000'.",
    )
    room_type: Optional[str] = Field(
        default="",
        description="Room type, for example 'phong tro', 'ky tuc xa', 'can ho', or 'studio'.",
    )


def get_room_search_tool(db: Session) -> StructuredTool:
    def search_rooms(
        district: Optional[str] = None,
        max_price: Optional[str] = None,
        room_type: Optional[str] = None,
    ) -> str:
        """Search available rooms from the database and return compact JSON."""
        try:
            # Subquery for thumbnail
            thumbnail_subq = (
                select(RoomImage.image_url)
                .where(RoomImage.room_id == Room.id)
                .order_by(RoomImage.id.asc())
                .limit(1)
                .correlate(Room)
                .scalar_subquery()
                .label("thumbnail")
            )

            query = (
                select(Post, Room, thumbnail_subq)
                .join(Room, Post.room_id == Room.id)
                .where(Post.status == "active")
                .where(Room.status == "available")
            )

            if district:
                clean_district = district.split(" ho")[0].split(" hay")[0].strip()
                hcm_keywords = ["hồ chí minh", "hcm", "tphcm", "ho chi minh", "thành phố hồ chí minh"]
                if clean_district.lower() not in hcm_keywords:
                    query = query.where(Room.district.ilike(f"%{clean_district}%"))
            if max_price:
                query = query.where(Room.price <= int(max_price))
            if room_type:
                query = query.where(Room.room_type.ilike(f"%{room_type}%"))

            rows = db.execute(query.limit(5)).all()

            if not rows:
                return json.dumps(
                    {
                        "message": "No matching rooms found. Tell the user the system has no available rooms for these criteria.",
                        "rooms_data": [],
                    },
                    ensure_ascii=False,
                )

            rooms_data = []
            for post, room, thumbnail in rows:
                address = room.full_address or f"{room.district}, {room.city}"

                rooms_data.append(
                    {
                        "id": post.id,
                        "room_id": room.id,
                        "title": post.title or room.title,
                        "price": room.price,
                        "thumbnail": thumbnail or "https://via.placeholder.com/150",
                        "address": address,
                    }
                )

            return json.dumps(
                {
                    "message": f"Found {len(rooms_data)} matching rooms. Reply briefly because the frontend renders the room cards.",
                    "rooms_data": rooms_data,
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {"message": f"Room query failed: {exc}", "rooms_data": []},
                ensure_ascii=False,
            )

    return StructuredTool.from_function(
        func=search_rooms,
        name="search_available_rooms",
        description="Search available rooms by district, budget, and room type.",
        args_schema=RoomSearchInput,
    )
