from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.rooms.room import Room

class RoomSearchInput(BaseModel):
    district: Optional[str] = Field(default=None, description="CHỈ truyền vào TÊN MỘT QUẬN DUY NHẤT (VD: 'Bình Thạnh', 'Thủ Đức'). Không truyền nhiều quận cùng lúc.")
    max_price: Optional[int] = Field(default=None, description="Mức giá tối đa mong muốn (đơn vị VNĐ). VD: 4000000 hoặc 5000000")
    room_type: Optional[str] = Field(default=None, description="Loại phòng. VD: 'Phòng trọ', 'Ký túc xá', 'Căn hộ', 'Studio'")

def get_room_search_tool(db: Session) -> StructuredTool:
    def search_rooms(district: Optional[str] = None, max_price: Optional[int] = None, room_type: Optional[str] = None) -> str:
        """Sử dụng công cụ này ĐỂ TÌM KIẾM phòng trọ từ Database khi người dùng có nhu cầu tìm phòng. Trả về văn bản chứa thông tin phòng."""
        try:
            # Query cơ bản
            query = select(Room).where(Room.status == "available")
            
            # Nếu user nhập nhiều quận (VD: 'Bình Thạnh hoặc Thủ Đức'), cắt lấy quận đầu tiên để tránh lỗi Like không match
            if district:
                clean_district = district.split(" ho")[0].split(" hay")[0].strip()
                query = query.where(Room.district.ilike(f"%{clean_district}%"))
            if max_price:
                query = query.where(Room.price <= max_price)
            if room_type:
                query = query.where(Room.room_type.ilike(f"%{room_type}%"))
                
            rooms = db.scalars(query.limit(5)).all()
            
            if not rooms:
                return f"[KẾT QUẢ TỪ DATABASE]: KHÔNG TÌM THẤY phòng nào phù hợp với (Quận: {district}, Giá dưới: {max_price}). Hãy báo người dùng là không có!"
                
            results = ["[KẾT QUẢ TỪ DATABASE]: Đã tìm thấy các phòng sau:"]
            for r in rooms:
                address = r.full_address or f"{r.district}, {r.city}"
                results.append(
                    f"- {r.title} (ID: {r.id})\n"
                    f"  Giá: {r.price:,.0f} VNĐ/tháng\n"
                    f"  Vị trí: {address}\n"
                    f"  Loại phòng: {r.room_type}, Diện tích: {r.area}m2\n"
                    f"  Liên hệ: {r.contact_phone} ({r.contact_name})"
                )
                
            return "\n".join(results)
        except Exception as e:
            return f"Lỗi khi truy vấn: {str(e)}"
            
    return StructuredTool.from_function(
        func=search_rooms,
        name="search_available_rooms",
        description="Tìm kiếm danh sách phòng trọ đang trống trong hệ thống dựa vào quận, giá tiền và loại phòng.",
        args_schema=RoomSearchInput
    )
