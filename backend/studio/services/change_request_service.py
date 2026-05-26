"""Validacao de solicitacoes de alteracao de agendamento."""

from django.utils.dateparse import parse_datetime

from studio.booking_utils import user_appointment_scope_queryset
from studio.models import Appointment, Tattooer
from studio.services.appointment_service import validate_schedule_and_conflict
from studio.services.exceptions import ServiceValidationError

CHANGE_REQUEST_ALLOWED_KEYS = frozenset(
    {
        "scheduled_at",
        "description",
        "appointment_kind",
        "tattooer",
        "clear_reference_image",
        "duration_minutes",
    }
)


def validate_change_request_write(attrs, context) -> dict:
    request = context.get("request")
    appointment = attrs.get("appointment") or getattr(
        context.get("instance"), "appointment", None
    )
    if appointment is None:
        raise ServiceValidationError({"appointment": "Obrigatorio."})
    if not request or not request.user.is_authenticated:
        raise ServiceValidationError("Sessao invalida.")
    if not user_appointment_scope_queryset(request.user).filter(pk=appointment.pk).exists():
        raise ServiceValidationError("Agendamento nao encontrado ou sem permissao.")

    changes = dict(attrs.pop("proposed_changes", {}) or {})
    legacy_dt = attrs.pop("proposed_scheduled_at", None)
    if legacy_dt is not None:
        changes["scheduled_at"] = legacy_dt.isoformat()

    unknown = set(changes.keys()) - CHANGE_REQUEST_ALLOWED_KEYS
    if unknown:
        raise ServiceValidationError(
            {"proposed_changes": f"Campos nao permitidos: {', '.join(sorted(unknown))}."}
        )

    ref_file = attrs.get("proposed_reference_image")
    if not changes and not ref_file:
        raise ServiceValidationError(
            {"proposed_changes": "Informe alteracoes ou envie uma nova imagem de referencia."}
        )

    if "tattooer" in changes:
        try:
            tid = int(changes["tattooer"])
        except (TypeError, ValueError) as exc:
            raise ServiceValidationError(
                {"proposed_changes": "tattooer deve ser um id numerico."}
            ) from exc
        if not Tattooer.objects.filter(pk=tid).exists():
            raise ServiceValidationError({"proposed_changes": "Tatuador invalido."})

    if "appointment_kind" in changes:
        if changes["appointment_kind"] not in (
            Appointment.KIND_SERVICE,
            Appointment.KIND_CONSULTATION,
        ):
            raise ServiceValidationError({"proposed_changes": "Modalidade invalida."})
    if "duration_minutes" in changes:
        try:
            dm = int(changes["duration_minutes"])
        except (TypeError, ValueError) as exc:
            raise ServiceValidationError(
                {"proposed_changes": "duration_minutes invalido."}
            ) from exc
        if dm < 15 or dm > 480:
            raise ServiceValidationError(
                {"proposed_changes": "Duracao deve estar entre 15 e 480 minutos."}
            )

    if "clear_reference_image" in changes:
        changes["clear_reference_image"] = str(changes["clear_reference_image"]).lower() in (
            "1",
            "true",
            "yes",
        )

    scheduled_at = None
    if "scheduled_at" in changes:
        scheduled_at = parse_datetime(str(changes["scheduled_at"]))
        if scheduled_at is None:
            raise ServiceValidationError(
                {"proposed_changes": "scheduled_at invalido (use ISO 8601)."}
            )

    tattooer_pk = int(changes["tattooer"]) if "tattooer" in changes else appointment.tattooer_id
    duration = (
        int(changes["duration_minutes"])
        if "duration_minutes" in changes
        else (appointment.duration_minutes or 60)
    )
    start = scheduled_at if scheduled_at is not None else appointment.scheduled_at
    sid = appointment.studio_id or (
        appointment.tattooer.studio_id if appointment.tattooer_id else None
    )
    validate_schedule_and_conflict(
        tattooer=Tattooer.objects.filter(pk=tattooer_pk).first() or appointment.tattooer,
        scheduled_at=start,
        duration_minutes=duration,
        studio_id=sid,
        appointment_kind=changes.get("appointment_kind", appointment.appointment_kind),
        exclude_appointment_id=appointment.pk,
    )

    attrs["proposed_payload"] = changes
    if scheduled_at is not None:
        attrs["proposed_scheduled_at"] = scheduled_at
    return attrs
