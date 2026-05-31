import re
from sqlalchemy.orm import Session
from app.repositories.chatbot.chat_repository import ChatRepository
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from fastapi import HTTPException, status
from app.core.config import settings

# Thêm module Agent và Tools
from langgraph.prebuilt import create_react_agent
from app.services.chatbot.tools.rooms_tool import get_room_search_tool

class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatRepository(db)
        # Sử dụng model llama3 (nhanh và miễn phí của Groq)
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant", 
            temperature=0.7,
            api_key=settings.groq_api_key
        )
        self.system_prompt = SystemMessage(
            content="""Bạn là AI hỗ trợ thân thiện của Roomie Match (Nền tảng tìm phòng). 
1. Nhiệm vụ của bạn là tư vấn tìm phòng và ghép trọ.
2. BẠN ĐƯỢC TRANG BỊ CÔNG CỤ TÌM KIẾM. Bạn PHẢI dùng công cụ này để tra cứu Database hệ thống dựa trên yêu cầu của user. KHÔNG TỰ BỊA RA PHÒNG.
3. Trả lời bằng Tiếng Việt. Giao tiếp như một nhân viên Sale: dạ, vâng, ạ.
4. KHI CÓ KẾT QUẢ TỪ CÔNG CỤ, BẠN PHẢI LIỆT KÊ CHI TIẾT THÔNG TIN PHÒNG (Tên, Giá, Địa chỉ, Liên hệ...) ra cho người dùng. TUYỆT ĐỐI KHÔNG trả lời chung chung là "có thể xem thông tin".
5. Nếu công cụ báo không có phòng, hãy lịch sự thông báo và đề xuất họ mở rộng tiêu chí.
6. TUYỆT ĐỐI KHÔNG BAO GIỜ in ra các cú pháp gọi hàm, source code (ví dụ như <function>, (function=... ), <tool_call>... ) trong câu trả lời của bạn.
"""
        )

    def create_session(self, user_id: int, title: str = "Trò chuyện mới"):
        return self.repo.create_session(user_id=user_id, title=title)
        
    def get_user_sessions(self, user_id: int):
        return self.repo.get_user_sessions(user_id=user_id)

    def get_session_messages(self, session_id: int):
        return self.repo.get_session_messages(session_id=session_id)

    def process_chat(self, user_id: int, session_id: int, text: str) -> str:
        session = self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session không tồn tại.")
        if session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập session này.")
            
        self.repo.add_message(session_id=session_id, role="user", content=text)
        
        db_messages = self.repo.get_session_messages(session_id=session_id)
        
        langchain_messages = []
        for msg in db_messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
                
        tools = [get_room_search_tool(self.db)]
        agent = create_react_agent(self.llm, tools=tools, prompt=self.system_prompt)
        
        response = agent.invoke({"messages": langchain_messages})
        
        ai_reply = str(response["messages"][-1].content)
        
        # --- BƯỚC DỌN DẸP / SANITIZE ---
        # Lược bỏ các đoạn text AI sinh nhầm mã Tool Calling (ảo giác) ra màn hình FE
        ai_reply = re.sub(r'\(function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        ai_reply = re.sub(r'\<tool_call\>.*?\</tool_call\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        # Bắt thêm trường hợp AI tạo cú pháp lỏng lẻo như /function=...
        ai_reply = re.sub(r'/function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        # Bắt thêm xml mở thẻ lỏng lẻo
        ai_reply = re.sub(r'\<function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        
        ai_reply = ai_reply.strip()
        
        self.repo.add_message(session_id=session_id, role="assistant", content=ai_reply)
        
        return ai_reply
