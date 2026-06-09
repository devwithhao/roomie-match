from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, model_validator


class ChatMessageBase(BaseModel):
    role: str
    content: str
    rooms_data: Optional[List[Dict[str, Any]]] = None


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    rooms_data: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def process_content_json(cls, data: Any) -> Any:
        import json
        if hasattr(data, 'content'):
            res = {
                "id": data.id,
                "session_id": data.session_id,
                "role": data.role,
                "content": data.content,
                "created_at": data.created_at,
                "rooms_data": None
            }
            try:
                parsed = json.loads(data.content)
                if isinstance(parsed, dict) and "content" in parsed:
                    res["content"] = parsed["content"]
                    res["rooms_data"] = parsed.get("rooms_data")
            except Exception:
                pass
            return res
        elif isinstance(data, dict) and 'content' in data:
            try:
                parsed = json.loads(data['content'])
                if isinstance(parsed, dict) and "content" in parsed:
                    data['content'] = parsed['content']
                    data['rooms_data'] = parsed.get("rooms_data")
            except:
                pass
        return data

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    content: str
