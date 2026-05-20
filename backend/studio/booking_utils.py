"""
Utilitarios de agenda: expediente, sobreposicao de horarios, change-requests e notificacoes.

user_appointment_scope_queryset() e o ponto unico de regra "quem ve quais agendamentos".
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from zoneinfo import ZoneInfo

from .models import (
    Appointment,
    AppointmentChangeRequest,
    InAppNotification,
    UserProfile,
)
from .studio_scope import ensure_profile_studio


def studio_timezone():
    name = getattr(settings, "TIME_ZONE", "UTC") or "UTC"
    return ZoneInfo(name)


def validate_scheduled_within_studio_hours(scheduled_at, studio_id: int | None = None):
    if scheduled_at is None:
        return
    from studio.features.studio_org.org_services import get_settings_for_studio
    from studio.studio_scope import default_studio

    sid = studio_id or default_studio().pk
    st = get_settings_for_studio(sid)
    tz = studio_timezone()
    if timezone.is_naive(scheduled_at):
        scheduled_at = timezone.make_aware(scheduled_at, tz)
    local = scheduled_at.astimezone(tz)
    day = local.date()
    opens = st.opens_at
    closes = st.closes_at
    open_dt = timezone.make_aware(datetime.combine(day, opens), tz)
    close_dt = timezone.make_aware(datetime.combine(day, closes), tz)
    latest_start = close_dt - timedelta(minutes=30)
    if open_dt >= close_dt:
        return
    if scheduled_at < open_dt or scheduled_at > latest_start:
        raise ValueError(
            "Horario fora do expediente do estudio ou muito proximo do fechamento "
            "(minimo 30 minutos antes do encerramento)."
        )


def appointment_intervals_overlap(start_a, minutes_a, start_b, minutes_b):
    end_a = start_a + timedelta(minutes=minutes_a)
    end_b = start_b + timedelta(minutes=minutes_b)
    return start_a < end_b and start_b < end_a


def change_request_responder_user_ids(appointment: Appointment, requester: User):
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=requester)
    role = profile.role
    ids = set()
    studio_id = appointment.studio_id
    if role == UserProfile.ROLE_CLIENT:
        if studio_id:
            ids.update(
                User.objects.filter(
                    profile__role=UserProfile.ROLE_STUDIO,
                    profile__studio_id=studio_id,
                ).values_list("id", flat=True)
            )
        else:
            ids.update(
                User.objects.filter(profile__role=UserProfile.ROLE_STUDIO).values_list(
                    "id", flat=True
                )
            )
        ids.update(
            User.objects.filter(profile__tattooer_id=appointment.tattooer_id).values_list(
                "id", flat=True
            )
        )
    elif role == UserProfile.ROLE_TATTOOER:
        if studio_id:
            ids.update(
                User.objects.filter(
                    profile__role=UserProfile.ROLE_STUDIO,
                    profile__studio_id=studio_id,
                ).values_list("id", flat=True)
            )
        em = (appointment.client.email or "").strip()
        if em:
            ids.update(User.objects.filter(email__iexact=em).values_list("id", flat=True))
    else:
        ids.update(
            User.objects.filter(profile__tattooer_id=appointment.tattooer_id).values_list(
                "id", flat=True
            )
        )
        em = (appointment.client.email or "").strip()
        if em:
            ids.update(User.objects.filter(email__iexact=em).values_list("id", flat=True))
    ids.discard(requester.id)
    return ids


def create_notifications_for_users(user_ids, message, link=""):
    for uid in user_ids:
        InAppNotification.objects.create(user_id=uid, message=message, link=link)


def notify_change_request_created(change_request):
    appt = change_request.appointment
    targets = change_request_responder_user_ids(appt, change_request.requested_by)
    if not targets:
        return
    msg = (
        f"Alteracao proposta no agendamento de {appt.client.name} "
        f"com {appt.tattooer.name}."
    )
    link = f"/agendamentos/{appt.id}/editar"
    create_notifications_for_users(targets, msg, link=link)
    from django.db import transaction

    from studio.features.notifications.appointment_mail_events import (
        notify_change_request_email_summary,
    )

    # E-mail so apos commit: evita avisar alteracao que foi revertida na transacao.
    transaction.on_commit(
        lambda: notify_change_request_email_summary(
            appt,
            "Uma nova solicitacao de alteracao foi registrada. Acesse o sistema para aceitar ou recusar.",
        )
    )


def user_appointment_scope_queryset(user):
    qs = Appointment.objects.all()
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    role = profile.role
    if role == UserProfile.ROLE_CLIENT:
        # Cliente ve agendamentos pelo e-mail do cadastro Client, nao por FK User->Client.
        email = (user.email or "").strip()
        if email:
            return qs.filter(client__email__iexact=email)
        return Appointment.objects.none()
    if role == UserProfile.ROLE_TATTOOER:
        if not profile.tattooer_id:
            return Appointment.objects.none()
        studio_id = ensure_profile_studio(profile)
        return qs.filter(tattooer_id=profile.tattooer_id, studio_id=studio_id)
    if role == UserProfile.ROLE_STUDIO:
        studio_id = ensure_profile_studio(profile)
        return qs.filter(studio_id=studio_id)
    return qs


def can_respond_to_change_request(user, change_request):
    if change_request.status != AppointmentChangeRequest.STATUS_PENDING:
        return False
    if change_request.requested_by_id == user.id:
        return False
    return user.id in change_request_responder_user_ids(
        change_request.appointment, change_request.requested_by
    )


def apply_accepted_change_request(change_request, request):
    from .serializers import AppointmentSerializer

    appt = change_request.appointment
    payload = dict(change_request.proposed_payload or {})
    data = {}
    if "scheduled_at" in payload:
        dt = parse_datetime(payload["scheduled_at"])
        if dt is None:
            raise ValueError("scheduled_at invalido na proposta.")
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, studio_timezone())
        data["scheduled_at"] = dt
    if "description" in payload:
        data["description"] = payload["description"]
    if "appointment_kind" in payload:
        data["appointment_kind"] = payload["appointment_kind"]
    if "tattooer" in payload:
        data["tattooer"] = int(payload["tattooer"])
    if "duration_minutes" in payload:
        data["duration_minutes"] = int(payload["duration_minutes"])

    if data:
        ser = AppointmentSerializer(
            appt,
            data=data,
            partial=True,
            context={"request": request, "applying_change_request_accept": True},
        )
        ser.is_valid(raise_exception=True)
        ser.save()

    cl = payload.get("clear_reference_image")
    if cl in (True, "true", 1, "1", "True", "TRUE"):
        appt.refresh_from_db()
        if appt.reference_image:
            appt.reference_image.delete(save=False)
        appt.reference_image = None
        appt.save(update_fields=["reference_image", "updated_at"])

    if change_request.proposed_reference_image:
        appt.refresh_from_db()
        src = change_request.proposed_reference_image
        if appt.reference_image:
            appt.reference_image.delete(save=False)
        appt.reference_image.save(src.name, src, save=True)

    return appt
