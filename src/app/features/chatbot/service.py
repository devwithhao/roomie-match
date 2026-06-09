import re
import json
from sqlalchemy.orm import Session
from app.features.chatbot.repositories.chat_repository import ChatRepository
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from fastapi import HTTPException, status
from app.core.config import settings

from langgraph.prebuilt import create_react_agent
from app.features.chatbot.tools.rooms_tool import get_room_search_tool

class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatRepository(db)
        self.llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0.7,
            api_key=settings.groq_api_key
        )
        self.system_prompt = SystemMessage(
            content="""You are Roomie, a friendly room-rental advisor for Roomie Match.
1. Be warm, concise, and helpful.
2. When the user asks to find rooms, always use the room search tool and base the reply on tool results.
3. If the tool returns rooms, briefly tell the user that matching rooms were found; do not list full details because the frontend renders cards.
4. If the tool returns no rooms, say that no rooms match the criteria and suggest changing filters.
5. Never invent room data.
"""
        )

    def create_session(self, user_id: int, title: str = "New Chat"):
        return self.repo.create_session(user_id=user_id, title=title)
        
    def get_user_sessions(self, user_id: int):
        return self.repo.get_user_sessions(user_id=user_id)

    def get_session_messages(self, session_id: int):
        return self.repo.get_session_messages(session_id=session_id)

    def process_chat(self, user_id: int, session_id: int, text: str) -> str:
        session = self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this session.")
            
        self.repo.add_message(session_id=session_id, role="user", content=text)
        
        db_messages = self.repo.get_session_messages(session_id=session_id)
        
        langchain_messages = []
        for msg in db_messages:
            content_str = msg.content
            if msg.role == "assistant":
                try:
                    parsed = json.loads(content_str)
                    if isinstance(parsed, dict) and "content" in parsed:
                        content_str = parsed["content"]
                except Exception:
                    pass

            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=content_str))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=content_str))
                
        tools = [get_room_search_tool(self.db)]
        agent = create_react_agent(self.llm, tools=tools, prompt=self.system_prompt)
        
        response = agent.invoke({"messages": langchain_messages})
        
        ai_reply = str(response["messages"][-1].content)
        
        ai_reply = re.sub(r'\(function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        ai_reply = re.sub(r'\<tool_call\>.*?\</tool_call\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        ai_reply = re.sub(r'/function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        ai_reply = re.sub(r'\<function=.*?\</function\>', '', ai_reply, flags=re.DOTALL | re.IGNORECASE)
        
        ai_reply = ai_reply.strip()
        
        # Extract room data from the room-search tool result, if present.
        rooms_data = None
        for msg in reversed(response["messages"]):
            if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") == "search_available_rooms":
                try:
                    tool_data = json.loads(msg.content)
                    if isinstance(tool_data, dict) and "rooms_data" in tool_data:
                        if len(tool_data["rooms_data"]) > 0:
                            rooms_data = tool_data["rooms_data"]
                except Exception:
                    pass
                break
        
        if rooms_data is not None:
            final_content = json.dumps({"content": ai_reply, "rooms_data": rooms_data}, ensure_ascii=False)
        else:
            final_content = json.dumps({"content": ai_reply, "rooms_data": []}, ensure_ascii=False)

        self.repo.add_message(session_id=session_id, role="assistant", content=final_content)
        
        return ai_reply
