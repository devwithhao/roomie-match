import json
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.rooms.room import Room


class RoomSearchInput(BaseModel):
    district: Optional[str] = Field(
        default=None,
        description="CHỈ truyền vào TÊN MỘT QUẬN DUY NHẤT (VD: 'Bình Thạnh', 'Thủ Đức'). Không truyền nhiều quận cùng lúc.",
    )
    max_price: Optional[str] = Field(
        default=None,
        description="Mức giá tối đa mong muốn (đơn vị VNĐ). VD: '4000000' hoặc '5000000'",
    )
    room_type: Optional[str] = Field(
        default=None,
        description="Loại phòng. VD: 'Phòng trọ', 'Ký túc xá', 'Căn hộ', 'Studio'",
    )


def get_room_search_tool(db: Session) -> StructuredTool:
    def search_rooms(
        district: Optional[str] = None,
        max_price: Optional[str] = None,
        room_type: Optional[str] = None,
    ) -> str:
        """Sử dụng công cụ này ĐỂ TÌM KIẾM phòng trọ từ Database khi người dùng có nhu cầu tìm phòng. Trả về văn bản JSON chứa thông tin phòng."""
        try:
            # Query cơ bản
            query = select(Room).where(Room.status == "available")

            # Nếu user nhập nhiều quận (VD: 'Bình Thạnh hoặc Thủ Đức'), cắt lấy quận đầu tiên để tránh lỗi Like không match
            if district:
                clean_district = district.split(" ho")[0].split(" hay")[0].strip()
                query = query.where(Room.district.ilike(f"%{clean_district}%"))
            if max_price:
                query = query.where(Room.price <= int(max_price))
            if room_type:
                query = query.where(Room.room_type.ilike(f"%{room_type}%"))

            rooms = db.scalars(query.limit(5)).all()

            if not rooms:
                return json.dumps({
                    "message": "Không tìm thấy kết quả nào. Hãy báo user là hết phòng.",
                    "rooms_data": []
                }, ensure_ascii=False)

            rooms_data = []
            for r in rooms:
                address = r.full_address or f"{r.district}, {r.city}"
                
                # Fetch thumbnail if any
                thumbnail = None
                if hasattr(r, 'images') and r.images:
                    thumbnail = r.images[0].image_url
                
                rooms_data.append({
                    "id": r.id,
                    "title": r.title,
                    "price": r.price,
                    "thumbnail": thumbnail or "https://via.placeholder.com/150",
                    "address": address
                })

            return json.dumps({
                "message": f"Tìm thấy {len(rooms_data)} phòng phù hợp. Hãy trả lời user một câu ngắn gọn như 'Dưới đây là các phòng tìm thấy:' vì FE đã tự render JSON rồi.",
                "rooms_data": rooms_data
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"message": f"Lỗi khi truy vấn: {str(e)}", "rooms_data": []}, ensure_ascii=False)

    return StructuredTool.from_function(
        func=search_rooms,
        name="search_available_rooms",
        description="Tìm kiếm danh sách phòng trọ đang trống trong hệ thống dựa vào quận, giá tiền và loại phòng.",
        args_schema=RoomSearchInput,
    )

