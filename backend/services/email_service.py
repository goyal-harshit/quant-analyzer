"""
email_service.py — minimal pluggable email transport.

Backends (via EMAIL_BACKEND):
  * console — log the message (default; zero-config dev).
  * memory  — append to an in-process outbox (tests assert on it).
  * smtp    — send via aiosmtplib if available (free SMTP: Brevo/Resend/Gmail).

Sending never raises into the caller — a transport failure is logged and swallowed
so an email hiccup can't break a request flow (reset/verify still return 200).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str


# In-process outbox for the "memory" backend (used by tests).
outbox: list[EmailMessage] = []


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send (or pretend to send) an email. Returns True on success/handled."""
    settings = get_settings()
    backend = (settings.email_backend or "console").lower()
    msg = EmailMessage(to=to, subject=subject, body=body)
    try:
        if backend == "memory":
            outbox.append(msg)
            return True
        if backend == "smtp":
            return await _send_smtp(settings, msg)
        # default: console
        logger.info("EMAIL[console] to=%s subject=%r\n%s", to, subject, body)
        return True
    except Exception as e:  # never propagate transport errors
        logger.warning("email send failed (to=%s): %s", to, e)
        return False


async def _send_smtp(settings, msg: EmailMessage) -> bool:
    if not settings.smtp_host:
        logger.warning("SMTP backend selected but SMTP_HOST unset — dropping email")
        return False
    try:
        import aiosmtplib
        from email.message import EmailMessage as MIMEMessage
    except Exception:
        logger.warning("aiosmtplib not installed — cannot send SMTP email")
        return False

    mime = MIMEMessage()
    mime["From"] = settings.email_from
    mime["To"] = msg.to
    mime["Subject"] = msg.subject
    mime.set_content(msg.body)

    await aiosmtplib.send(
        mime,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_starttls,
    )
    return True


def clear_outbox() -> None:
    outbox.clear()
