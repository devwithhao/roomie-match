from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.features.chatbot.models.chat_session import ChatSession
from app.features.chatbot.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, title: str = "New Chat") -> ChatSession:
        db_session = ChatSession(user_id=user_id, title=title)
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def get_session(self, session_id: int) -> ChatSession | None:
        return self.db.scalar(select(ChatSession).where(ChatSession.id == session_id))

    def get_user_sessions(self, user_id: int) -> list[ChatSession]:
        return list(
            self.db.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc())
            )
        )

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)

        # Keep the parent session ordered by recent activity.
        session = self.get_session(session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_session_messages(self, session_id: int) -> list[ChatMessage]:
        return list(
            self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
        )
