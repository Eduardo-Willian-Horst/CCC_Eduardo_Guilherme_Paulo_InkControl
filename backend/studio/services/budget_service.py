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
    if appointment.status in (Appointment.STATUS_DONE, Appointment.STATUS_CANCELLED):
        raise ServiceValidationError("Agendamento encerrado ou cancelado.")
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
    if move_to_waiting_budget and appointment.status == Appointment.STATUS_REQUESTED:
        if Appointment.can_transition(appointment.status, Appointment.STATUS_WAITING_BUDGET):
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
