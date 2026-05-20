"""HU20: e-mail em toda tentativa de pagamento da mensalidade."""

from studio.features.notifications.email_service import send_plain_email
from studio.models import StudioBilling


def notify_payment_attempt(
    billing: StudioBilling,
    *,
    ok: bool,
    note: str,
    recipient_emails: list[str],
) -> None:
    recipients = [e for e in recipient_emails if e]
    if not recipients:
        return
    if ok:
        subject = "[InkControl] Pagamento da mensalidade — sucesso"
        body = (
            f"Pagamento registrado com sucesso.\n"
            f"Estudio: {billing.studio.name}\n"
            f"Detalhe: {note}\n"
            f"Acesso ate: {billing.paid_until.isoformat()}\n"
        )
    else:
        subject = "[InkControl] Pagamento da mensalidade — falha"
        body = (
            f"A tentativa de pagamento nao foi concluida.\n"
            f"Estudio: {billing.studio.name}\n"
            f"Motivo: {note}\n"
            f"Acesso ate (inalterado): {billing.paid_until.isoformat()}\n"
        )
    send_plain_email(subject, body, recipients)
