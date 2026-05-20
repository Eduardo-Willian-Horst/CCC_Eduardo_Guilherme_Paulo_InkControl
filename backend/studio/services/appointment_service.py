"""
Regras de agendamento: HU12, expediente, conflito de horario, transicoes de status.
"""

from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from studio.booking_utils import (
    appointment_intervals_overlap,
    validate_scheduled_within_studio_hours,
)
from studio.health_snapshot import build_health_snapshot
from studio.models import Appointment, Tattooer, UserProfile
from studio.services.exceptions import ServiceValidationError
from studio.studio_scope import get_user_studio_id

AGENDA_FIELD_NAMES = frozenset(
    {
        "scheduled_at",
        "description",
        "appointment_kind",
        "tattooer",
        "client",
        "reference_image",
        "duration_minutes",
    }
)


def validate_consultation_offered(studio_id: int, appointment_kind: str) -> None:
    if appointment_kind != Appointment.KIND_CONSULTATION:
        return
    from studio.features.studio_org.org_services import get_settings_for_studio

    if not get_settings_for_studio(studio_id).offers_consultation:
        raise ServiceValidationError(
            {
                "appointment_kind": (
                    "Este estudio nao oferece agendamento de avaliacao (HU12)."
                )
            }
        )


def resolve_studio_id(attrs, instance, request) -> int | None:
    tattooer = attrs.get("tattooer", getattr(instance, "tattooer", None) if instance else None)
    studio_id = attrs.get("studio_id")
    if studio_id is None and hasattr(attrs.get("studio"), "id"):
        studio_id = attrs["studio"].id
    if studio_id is None and tattooer is not None:
        studio_id = tattooer.studio_id
    if studio_id is None and instance is not None:
        studio_id = instance.studio_id
    if studio_id is None and request and request.user.is_authenticated:
        studio_id = get_user_studio_id(request.user)
    return studio_id


def enforce_agenda_fields_via_change_request(user: User, attrs: dict, instance) -> None:
    from studio.permissions import get_user_role

    role = get_user_role(user)
    if role in (UserProfile.ROLE_CLIENT, UserProfile.ROLE_TATTOOER):
        touched = AGENDA_FIELD_NAMES.intersection(attrs.keys())
        if touched:
            raise ServiceValidationError(
                {
                    k: (
                        "Alteracao sujeita a aceite: envie uma solicitacao em "
                        "/api/appointment-change-requests/."
                    )
                    for k in sorted(touched)
                }
            )


def validate_status_transition(instance, next_status: str) -> None:
    if not Appointment.can_transition(instance.status, next_status):
        raise ServiceValidationError(
            {
                "status": (
                    f"Transicao invalida de '{instance.status}' para '{next_status}'."
                )
            }
        )


def validate_schedule_and_conflict(
    *,
    tattooer,
    scheduled_at,
    duration_minutes: int,
    studio_id: int | None,
    appointment_kind: str,
    exclude_appointment_id: int | None = None,
) -> None:
    if studio_id:
        validate_consultation_offered(studio_id, appointment_kind)
    if tattooer is None or scheduled_at is None:
        return
    try:
        validate_scheduled_within_studio_hours(scheduled_at, studio_id=studio_id)
    except ValueError as exc:
        raise ServiceValidationError({"scheduled_at": str(exc)}) from exc
    conflict_query = Appointment.objects.filter(tattooer=tattooer).exclude(
        status=Appointment.STATUS_CANCELLED
    )
    if exclude_appointment_id:
        conflict_query = conflict_query.exclude(pk=exclude_appointment_id)
    for other in conflict_query.only("scheduled_at", "duration_minutes"):
        od = other.duration_minutes or 60
        if appointment_intervals_overlap(scheduled_at, duration_minutes, other.scheduled_at, od):
            raise ServiceValidationError(
                {
                    "scheduled_at": (
                        "Conflito de horario com outra sessao deste tatuador "
                        "(intervalos sobrepostos)."
                    )
                }
            )


def validate_appointment_write(attrs, instance, context) -> dict:
    request = context.get("request")
    if request and instance and not context.get("applying_change_request_accept"):
        enforce_agenda_fields_via_change_request(request.user, attrs, instance)
    if instance and "status" in attrs:
        validate_status_transition(instance, attrs["status"])
        if attrs["status"] == Appointment.STATUS_WAITING_BUDGET:
            if not instance.budget_amount and not attrs.get("budget_amount"):
                raise ServiceValidationError(
                    {
                        "status": (
                            "Informe o orcamento em POST/PATCH /api/appointments/{id}/budget/ "
                            "antes de marcar como aguardando orcamento."
                        )
                    }
                )
    tattooer = attrs.get("tattooer", getattr(instance, "tattooer", None) if instance else None)
    scheduled_at = attrs.get(
        "scheduled_at", getattr(instance, "scheduled_at", None) if instance else None
    )
    duration = attrs.get(
        "duration_minutes",
        getattr(instance, "duration_minutes", None) if instance else None,
    )
    if duration is None:
        duration = 60
    kind = attrs.get(
        "appointment_kind",
        getattr(instance, "appointment_kind", Appointment.KIND_SERVICE) if instance else Appointment.KIND_SERVICE,
    )
    studio_id = resolve_studio_id(attrs, instance, request)
    validate_schedule_and_conflict(
        tattooer=tattooer,
        scheduled_at=scheduled_at,
        duration_minutes=duration,
        studio_id=studio_id,
        appointment_kind=kind,
        exclude_appointment_id=instance.pk if instance else None,
    )
    return attrs


def prepare_appointment_create(validated_data: dict, request) -> dict:
    client = validated_data.get("client")
    if client is not None and not validated_data.get("health_snapshot"):
        validated_data["health_snapshot"] = build_health_snapshot(client)
    if request and request.user.is_authenticated and not validated_data.get("studio"):
        validated_data["studio_id"] = get_user_studio_id(request.user)
    tattooer = validated_data.get("tattooer")
    if tattooer and tattooer.studio_id and not validated_data.get("studio_id"):
        validated_data["studio_id"] = tattooer.studio_id
    kind = validated_data.get("appointment_kind", Appointment.KIND_SERVICE)
    studio_id = validated_data.get("studio_id")
    if studio_id:
        validate_consultation_offered(studio_id, kind)
    return validated_data


def service_error_to_drf(exc: ServiceValidationError):
    return serializers.ValidationError(exc.detail)
