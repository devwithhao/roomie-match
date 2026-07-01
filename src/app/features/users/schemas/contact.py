from __future__ import annotations

from pydantic import BaseModel, EmailStr

class ContactMessageRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    topic: str
    message: str
    attachment_name: str | None = None
