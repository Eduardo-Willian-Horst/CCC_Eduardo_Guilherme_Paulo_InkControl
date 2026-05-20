"""
E-mails transacionais de agendamento (HU19).

Envio via transaction.on_commit para nao notificar operacoes revertidas.
"""

from django.db import transaction

from studio.features.notifications.appointment_email import recipient_emails_for_appointment
from studio.features.notifications.email_service import send_plain_email


def _schedule_email(subject: str, body: str, recipients: list[str]) -> None:
    transaction.on_commit(lambda: send_plain_email(subject, body, recipients))


def notify_appointment_created(appointment) -> None:
    subject = f"[InkControl] Novo agendamento #{appointment.pk}"
    body = (
        f"Agendamento #{appointment.pk}\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"Data/hora: {appointment.scheduled_at.isoformat()}\n"
        f"Status: {appointment.status}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_appointment_status_change(appointment, old_status: str) -> None:
    subject = f"[InkControl] Agendamento #{appointment.pk} atualizado"
    body = (
        f"Agendamento #{appointment.pk}\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"Data/hora: {appointment.scheduled_at.isoformat()}\n"
        f"Status anterior: {old_status}\n"
        f"Status atual: {appointment.status}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_appointment_cancelled(appointment) -> None:
    subject = f"[InkControl] Agendamento #{appointment.pk} cancelado"
    body = (
        f"O agendamento #{appointment.pk} foi cancelado.\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"Data/hora prevista: {appointment.scheduled_at.isoformat()}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_change_request_email_summary(appointment, summary: str) -> None:
    subject = f"[InkControl] Solicitacao de alteracao — agendamento #{appointment.pk}"
    body = (
        f"Agendamento #{appointment.pk}\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"{summary}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_change_request_accepted(appointment) -> None:
    notify_change_request_email_summary(
        appointment,
        "A solicitacao de alteracao foi ACEITA e o agendamento foi atualizado.",
    )


def notify_change_request_rejected(appointment) -> None:
    notify_change_request_email_summary(
        appointment,
        "A solicitacao de alteracao foi RECUSADA. O horario anterior permanece.",
    )
