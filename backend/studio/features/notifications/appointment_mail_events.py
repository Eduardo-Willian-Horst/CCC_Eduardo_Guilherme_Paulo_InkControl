"""
Notificacoes transacionais de agendamento (in-app + e-mail).

E-mails sao enviados via transaction.on_commit para nao notificar operacoes revertidas.
"""

from django.contrib.auth.models import User
from django.db import transaction

from studio.features.notifications.appointment_email import recipient_emails_for_appointment
from studio.features.notifications.email_service import send_plain_email
from studio.models import Appointment, InAppNotification, UserProfile


def _schedule_email(subject: str, body: str, recipients: list[str]) -> None:
    transaction.on_commit(lambda: send_plain_email(subject, body, recipients))


def _appointment_link(appointment: Appointment) -> str:
    return f"/agendamentos/{appointment.pk}/editar"


def _participant_user_ids(appointment: Appointment) -> set[int]:
    user_ids = set()
    studio_id = appointment.studio_id
    studio_users = User.objects.filter(profile__role=UserProfile.ROLE_STUDIO)
    if studio_id:
        studio_users = studio_users.filter(profile__studio_id=studio_id)
    user_ids.update(studio_users.values_list("id", flat=True))
    user_ids.update(
        User.objects.filter(profile__tattooer_id=appointment.tattooer_id).values_list(
            "id",
            flat=True,
        )
    )
    client_email = (appointment.client.email or "").strip()
    if client_email:
        user_ids.update(User.objects.filter(email__iexact=client_email).values_list("id", flat=True))
    return user_ids


def _notify_in_app(appointment: Appointment, message: str, actor=None) -> None:
    user_ids = _participant_user_ids(appointment)
    if actor and getattr(actor, "is_authenticated", False):
        user_ids.discard(actor.id)
    if not user_ids:
        return
    link = _appointment_link(appointment)
    for user_id in user_ids:
        InAppNotification.objects.create(user_id=user_id, message=message, link=link)


def _status_label(status: str) -> str:
    labels = {
        Appointment.STATUS_REQUESTED: "solicitado",
        Appointment.STATUS_WAITING_BUDGET: "orcamento enviado",
        Appointment.STATUS_CONFIRMED: "confirmado",
        Appointment.STATUS_IN_PROGRESS: "em andamento",
        Appointment.STATUS_DONE: "concluido",
        Appointment.STATUS_CANCELLED: "cancelado",
    }
    return labels.get(status, status)


def notify_appointment_created(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Novo agendamento de {appointment.client.name} com {appointment.tattooer.name}.",
        actor=actor,
    )
    subject = f"[InkControl] Novo agendamento #{appointment.pk}"
    body = (
        f"Agendamento #{appointment.pk}\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"Data/hora: {appointment.scheduled_at.isoformat()}\n"
        f"Status: {appointment.status}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_appointment_status_change(appointment, old_status: str, actor=None) -> None:
    _notify_in_app(
        appointment,
        (
            f"Agendamento de {appointment.client.name} com {appointment.tattooer.name} "
            f"mudou de {_status_label(old_status)} para {_status_label(appointment.status)}."
        ),
        actor=actor,
    )
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


def notify_appointment_updated(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Agendamento de {appointment.client.name} com {appointment.tattooer.name} foi atualizado.",
        actor=actor,
    )


def notify_appointment_cancelled(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Agendamento de {appointment.client.name} com {appointment.tattooer.name} foi cancelado.",
        actor=actor,
    )
    subject = f"[InkControl] Agendamento #{appointment.pk} cancelado"
    body = (
        f"O agendamento #{appointment.pk} foi cancelado.\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"Data/hora prevista: {appointment.scheduled_at.isoformat()}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_appointment_budget_sent(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Orcamento enviado para o agendamento de {appointment.client.name} com {appointment.tattooer.name}.",
        actor=actor,
    )


def notify_change_request_email_summary(appointment, summary: str) -> None:
    subject = f"[InkControl] Solicitacao de alteracao — agendamento #{appointment.pk}"
    body = (
        f"Agendamento #{appointment.pk}\n"
        f"Cliente: {appointment.client.name}\n"
        f"Tatuador: {appointment.tattooer.name}\n"
        f"{summary}\n"
    )
    _schedule_email(subject, body, recipient_emails_for_appointment(appointment))


def notify_change_request_accepted(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Solicitacao de alteracao aceita no agendamento de {appointment.client.name}.",
        actor=actor,
    )
    notify_change_request_email_summary(
        appointment,
        "A solicitacao de alteracao foi ACEITA e o agendamento foi atualizado.",
    )


def notify_change_request_rejected(appointment, actor=None) -> None:
    _notify_in_app(
        appointment,
        f"Solicitacao de alteracao recusada no agendamento de {appointment.client.name}.",
        actor=actor,
    )
    notify_change_request_email_summary(
        appointment,
        "A solicitacao de alteracao foi RECUSADA. O horario anterior permanece.",
    )
