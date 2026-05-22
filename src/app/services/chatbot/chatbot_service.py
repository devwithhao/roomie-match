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
            content="""Bạn là AI hỗ trợ của Roomie Match (Nền tảng tìm phòng). 
1. Nhiệm vụ của bạn là tư vấn phòng, ghép trọ, và hỗ trợ các tính năng.
2. LUÔN LUÔN gọi tool search_available_rooms khi người dùng hỏi tìm phòng. Nếu cần hỏi thêm thông tin (giá, quận), hãy hỏi người dùng.
3. KHI TOOL TRẢ VỀ KẾT QUẢ KHÔNG TÌM THẤY, GHI RÕ: "Hiện tại hệ thống không có phòng nào phù hợp với yêu cầu của bạn, bạn có thể tăng ngân sách hoặc đổi khu vực không?", TUYỆT ĐỐI KHÔNG tự bịa ra phòng ở khu vực khác.
4. Trả lời ngắn gọn, thân thiện bằng Tiếng Việt.
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
        
        self.repo.add_message(session_id=session_id, role="assistant", content=ai_reply)
        
        return ai_reply
