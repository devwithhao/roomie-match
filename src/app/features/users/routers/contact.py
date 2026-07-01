from __future__ import annotations

import logging
from fastapi import APIRouter

from app.features.users.schemas.contact import ContactMessageRequest
from app.core.email import send_email_sync
from app.core.config import settings

router = APIRouter()

@router.post("/messages")
def send_contact_message(data: ContactMessageRequest) -> dict:
    subject = f"[RommieMatch Liên hệ] {data.topic} - từ {data.first_name} {data.last_name}"
    content = f"""Có một yêu cầu hỗ trợ mới từ ứng dụng RommieMatch:

- Họ tên: {data.first_name} {data.last_name}
- Email: {data.email}
- Số điện thoại: {data.phone or 'Không cung cấp'}
- Chủ đề: {data.topic}
- Có đính kèm file: {data.attachment_name or 'Không'}

Nội dung tin nhắn:
{data.message}
"""
    
    # Send email to the admin email (configured in SMTP_USER)
    admin_email = settings.smtp_user
    if admin_email:
        send_email_sync(
            to_email=admin_email, 
            subject=subject, 
            content=content, 
            reply_to=data.email
        )
    else:
        logging.getLogger(__name__).warning("No SMTP user configured to receive contact messages.")

    return {"message": "Success"}
