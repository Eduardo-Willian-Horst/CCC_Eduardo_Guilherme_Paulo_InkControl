"""
Orcamento (status waiting_budget): envio e atualizacao pelo estudio/tatuador.
"""

from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.utils import timezone

from studio.models import Appointment, UserProfile
from studio.permissions import get_user_role
from studio.services.exceptions import ServiceValidationError


def _can_manage_budget(user: User) -> bool:
    return get_user_role(user) in (UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER)


def _can_client_respond_budget(user: User, appointment: Appointment) -> bool:
    if get_user_role(user) != UserProfile.ROLE_CLIENT:
        return False
    return (user.email or "").strip().lower() == (appointment.client.email or "").strip().lower()


def submit_or_update_budget(
    appointment: Appointment,
    user: User,
    *,
    amount,
    notes: str = "",
    move_to_waiting_budget: bool = True,
) -> Appointment:
    if not _can_manage_budget(user):
        raise ServiceValidationError("Sem permissao para definir orcamento.")
    if appointment.appointment_kind != Appointment.KIND_SERVICE:
        raise ServiceValidationError(
            {"appointment_kind": "Orcamento so pode ser enviado para sessao."}
        )
    if appointment.status in (Appointment.STATUS_DONE, Appointment.STATUS_CANCELLED):
        raise ServiceValidationError("Agendamento encerrado ou cancelado.")
    if appointment.status not in (
        Appointment.STATUS_REQUESTED,
        Appointment.STATUS_WAITING_BUDGET,
    ):
        raise ServiceValidationError("Orcamento so pode ser enviado antes da confirmacao.")
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError) as exc:
        raise ServiceValidationError({"budget_amount": "Valor invalido."}) from exc
    if decimal_amount <= 0:
        raise ServiceValidationError({"budget_amount": "Valor deve ser maior que zero."})

    appointment.budget_amount = decimal_amount
    appointment.budget_notes = (notes or "")[:2000]
    appointment.budget_sent_at = timezone.now()
    appointment.budget_sent_by = user
    if appointment.status == Appointment.STATUS_REQUESTED:
        appointment.status = Appointment.STATUS_WAITING_BUDGET
    appointment.save(
        update_fields=[
            "budget_amount",
            "budget_notes",
            "budget_sent_at",
            "budget_sent_by",
            "status",
            "updated_at",
        ]
    )
    return appointment


def accept_budget(appointment: Appointment, user: User) -> Appointment:
    if not _can_client_respond_budget(user, appointment):
        raise ServiceValidationError("Sem permissao para responder este orcamento.")
    if appointment.status != Appointment.STATUS_WAITING_BUDGET:
        raise ServiceValidationError("Este agendamento nao esta aguardando aceite de orcamento.")
    if not appointment.budget_amount:
        raise ServiceValidationError("Nao ha orcamento enviado para este agendamento.")
    appointment.status = Appointment.STATUS_CONFIRMED
    appointment.save(update_fields=["status", "updated_at"])
    return appointment


def reject_budget(appointment: Appointment, user: User) -> Appointment:
    if not _can_client_respond_budget(user, appointment):
        raise ServiceValidationError("Sem permissao para responder este orcamento.")
    if appointment.status != Appointment.STATUS_WAITING_BUDGET:
        raise ServiceValidationError("Este agendamento nao esta aguardando aceite de orcamento.")
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.save(update_fields=["status", "updated_at"])
    return appointment
