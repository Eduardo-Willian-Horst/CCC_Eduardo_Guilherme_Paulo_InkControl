"""Envio de e-mail transacional (SMTP ou console em dev)."""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_plain_email(subject: str, body: str, to_emails: list[str]) -> None:
    if not to_emails:
        return
    recipients = [e.strip() for e in to_emails if e and str(e).strip()]
    if not recipients:
        return
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", settings.DEBUG)
    try:
        send_mail(subject, body, from_email, recipients, fail_silently=fail_silently)
    except Exception:
        logger.exception("Falha ao enviar e-mail: %s", subject)
