from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.api.v1.auth.deps import get_current_account
from app.models.users.account import Account
from app.schemas.chatbot.chat import (
    ChatSessionResponse, 
    ChatSessionCreate, 
    ChatRequest, 
    ChatMessageResponse
)
from app.services.chatbot.chatbot_service import ChatbotService

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_account: Account = Depends(get_current_account),
):
    service = ChatbotService(db)
    return service.create_session(user_id=current_account.id, title=request.title)


@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_user_sessions(
    db: Session = Depends(get_db),
    current_account: Account = Depends(get_current_account),
):
    service = ChatbotService(db)
    return service.get_user_sessions(user_id=current_account.id)


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_account: Account = Depends(get_current_account),
):
    service = ChatbotService(db)
    # Xác thực session là của user này
    session = service.repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session không tồn tại.")
    if session.user_id != current_account.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Bạn không có quyền truy cập session này."
        )

    return service.get_session_messages(session_id=session_id)


@router.post("/sessions/{session_id}/chat", response_model=ChatMessageResponse)
def send_chat_message(
    session_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_account: Account = Depends(get_current_account),
):
    service = ChatbotService(db)
    # Quá trình process_chat đã có sẵn validate user
    service.process_chat(
        user_id=current_account.id, 
        session_id=session_id, 
        text=request.content
    )
    
    # Lấy message (assistant reply) cuối cùng để trả về
    messages = service.get_session_messages(session_id=session_id)
    if messages:
        return messages[-1]
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Lỗi khi tạo phản hồi từ AI."
    )
