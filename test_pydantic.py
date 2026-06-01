from pydantic import BaseModel, ConfigDict, model_validator
from typing import Any, List, Optional, Dict
from datetime import datetime
import json

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
        return data
        
    model_config = ConfigDict(from_attributes=True)

class MockModel:
    def __init__(self):
        self.id = 1
        self.session_id = 1
        self.role = "assistant"
        self.content = '{"content": "Hello", "rooms_data": [{"id": 1, "title": "Room 1"}]}'
        self.created_at = datetime.now()

mock = MockModel()
print(ChatMessageResponse.model_validate(mock).model_dump_json())
