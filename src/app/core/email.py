import smtplib
from email.message import EmailMessage
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_email_sync(to_email: str, subject: str, content: str, reply_to: str | None = None) -> bool:
    """
    Sends an email using smtplib.
    Returns True if successful, False otherwise.
    """
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP configuration is missing. Email not sent.")
        # Fallback to demo mode logging
        logger.info(f"\n[DEMO EMAIL]\nTo: {to_email}\nSubject: {subject}\nBody:\n{content}\n")
        return False

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    
    if reply_to:
        msg["Reply-To"] = reply_to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
