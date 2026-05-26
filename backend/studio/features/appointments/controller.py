"""
Agendamentos e solicitacoes de alteracao (change-request).

Escopo por papel via user_appointment_scope_queryset; e-mails em create/cancel/accept/reject.
"""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from studio.booking_utils import (
    apply_accepted_change_request,
    can_respond_to_change_request,
    notify_change_request_created,
    user_appointment_scope_queryset,
)
from studio.models import (
    Appointment,
    AppointmentChangeRequest,
    UserProfile,
)
from studio.permissions import RoleByActionPermission, get_user_role
from studio.serializers import (
    AppointmentBudgetSerializer,
    AppointmentChangeRequestSerializer,
    AppointmentReadSerializer,
    AppointmentSerializer,
)
from studio.services.appointment_service import ensure_client_has_health_form, service_error_to_drf
from studio.services.budget_service import (
    accept_budget as accept_appointment_budget,
    reject_budget as reject_appointment_budget,
    submit_or_update_budget,
)
from studio.services.exceptions import ServiceValidationError

from studio.features.auth.utils import get_or_create_client_for_app_user
from studio.features.notifications.appointment_mail_events import (
    notify_appointment_budget_sent,
    notify_appointment_cancelled,
    notify_appointment_created,
    notify_appointment_status_change,
    notify_appointment_updated,
    notify_change_request_accepted,
    notify_change_request_rejected,
)


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related(
        "client",
        "tattooer",
        "client__health_form",
        "source_consultation",
    )
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "partial_update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "destroy": {UserProfile.ROLE_STUDIO},
        "cancel": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "confirm": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "start": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "complete": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "budget": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "accept_budget": {UserProfile.ROLE_CLIENT},
        "reject_budget": {UserProfile.ROLE_CLIENT},
    }

    def get_serializer_class(self):
        if getattr(self, "action", None) in ("list", "retrieve"):
            return AppointmentReadSerializer
        return AppointmentSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if getattr(self, "action", None) == "create" and self.request.user.is_authenticated:
            ctx["client_booking"] = get_user_role(self.request.user) == UserProfile.ROLE_CLIENT
        return ctx

    def perform_create(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            tattooer = serializer.validated_data.get("tattooer")
            target_studio_id = tattooer.studio_id if tattooer else None
            client = get_or_create_client_for_app_user(
                self.request.user,
                studio_id=target_studio_id,
            )
            try:
                ensure_client_has_health_form(client)
            except ServiceValidationError as exc:
                raise service_error_to_drf(exc) from exc
            instance = serializer.save(client=client)
        else:
            instance = serializer.save()
        notify_appointment_created(instance, actor=self.request.user)

    def perform_update(self, serializer):
        fields_to_notify = {
            "client",
            "tattooer",
            "scheduled_at",
            "description",
            "appointment_kind",
            "duration_minutes",
            "reference_image",
        }
        tracked_fields = fields_to_notify.intersection(serializer.validated_data.keys())
        old_values = {field: getattr(serializer.instance, field) for field in tracked_fields}
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            appointment = serializer.save(client=client)
        else:
            appointment = serializer.save()
        changed = any(
            old_values[field] != getattr(appointment, field)
            for field in tracked_fields
        )
        if changed:
            notify_appointment_updated(appointment, actor=self.request.user)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if not Appointment.can_transition(appointment.status, Appointment.STATUS_CANCELLED):
            return Response(
                {"detail": "Nao e possivel cancelar este agendamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.STATUS_CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        notify_appointment_cancelled(appointment, actor=request.user)
        serializer = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(serializer.data)

    def _transition_status(self, request, appointment, next_status):
        if appointment.status == next_status:
            return Response(
                {"detail": "Esta acao ja foi aplicada a este agendamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Appointment.can_transition(appointment.status, next_status):
            return Response(
                {"detail": "Nao e possivel executar esta acao neste agendamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if appointment.appointment_kind == Appointment.KIND_SERVICE and next_status == Appointment.STATUS_CONFIRMED:
            return Response(
                {
                    "detail": (
                        "Envie o orcamento da sessao. Ela sera confirmada quando "
                        "o cliente aceitar."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        old_status = appointment.status
        appointment.status = next_status
        appointment.save(update_fields=["status", "updated_at"])
        notify_appointment_status_change(appointment, old_status, actor=request.user)
        serializer = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        return self._transition_status(request, appointment, Appointment.STATUS_CONFIRMED)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        appointment = self.get_object()
        return self._transition_status(request, appointment, Appointment.STATUS_IN_PROGRESS)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        appointment = self.get_object()
        return self._transition_status(request, appointment, Appointment.STATUS_DONE)

    @action(detail=True, methods=["get", "post", "patch"], url_path="budget")
    def budget(self, request, pk=None):
        """Orcamento da sessao (waiting_budget): GET leitura; POST/PATCH envio pelo estudio/tatuador."""
        appointment = self.get_object()
        if request.method == "GET":
            return Response(
                {
                    "budget_amount": appointment.budget_amount,
                    "budget_currency": appointment.budget_currency,
                    "budget_notes": appointment.budget_notes,
                    "budget_sent_at": appointment.budget_sent_at,
                    "status": appointment.status,
                }
            )
        ser = AppointmentBudgetSerializer(data=request.data, partial=request.method == "PATCH")
        ser.is_valid(raise_exception=True)
        old_budget_sent_at = appointment.budget_sent_at
        old_status = appointment.status
        try:
            appointment = submit_or_update_budget(
                appointment,
                request.user,
                amount=ser.validated_data["budget_amount"],
                notes=ser.validated_data.get("budget_notes", ""),
                move_to_waiting_budget=ser.validated_data.get("move_to_waiting_budget", True),
            )
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc)
        if old_status != appointment.status:
            notify_appointment_status_change(appointment, old_status, actor=request.user)
        elif old_budget_sent_at != appointment.budget_sent_at:
            notify_appointment_budget_sent(appointment, actor=request.user)
        out = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(out.data)

    @action(detail=True, methods=["post"], url_path="budget/accept")
    def accept_budget(self, request, pk=None):
        appointment = self.get_object()
        old_status = appointment.status
        try:
            appointment = accept_appointment_budget(appointment, request.user)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc)
        if old_status != appointment.status:
            notify_appointment_status_change(appointment, old_status, actor=request.user)
        out = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(out.data)

    @action(detail=True, methods=["post"], url_path="budget/reject")
    def reject_budget(self, request, pk=None):
        appointment = self.get_object()
        old_status = appointment.status
        try:
            appointment = reject_appointment_budget(appointment, request.user)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc)
        if old_status != appointment.status:
            notify_appointment_status_change(appointment, old_status, actor=request.user)
        out = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(out.data)

    def get_queryset(self):
        # Base: regra central de visibilidade (studio / tatuador / cliente).
        queryset = user_appointment_scope_queryset(self.request.user).select_related(
            "client", "tattooer", "client__health_form", "source_consultation"
        )
        q = self.request.query_params.get("q")
        status_filter = self.request.query_params.get("status")
        tattooer_filter = self.request.query_params.get("tattooer")
        client_filter = self.request.query_params.get("client")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        period = self.request.query_params.get("period")
        base_date_raw = self.request.query_params.get("date")
        kind = self.request.query_params.get("appointment_kind")

        if kind in (Appointment.KIND_SERVICE, Appointment.KIND_CONSULTATION):
            queryset = queryset.filter(appointment_kind=kind)

        if q:
            queryset = queryset.filter(
                Q(description__icontains=q)
                | Q(client__name__icontains=q)
                | Q(tattooer__name__icontains=q)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if tattooer_filter and tattooer_filter.isdigit():
            queryset = queryset.filter(tattooer_id=int(tattooer_filter))
        if client_filter and client_filter.isdigit():
            if get_user_role(self.request.user) != UserProfile.ROLE_CLIENT:
                queryset = queryset.filter(client_id=int(client_filter))
        if date_from:
            parsed_from = parse_date(date_from)
            if parsed_from:
                tz = timezone.get_current_timezone()
                start_from = timezone.make_aware(datetime.combine(parsed_from, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_from)
        if date_to:
            parsed_to = parse_date(date_to)
            if parsed_to:
                tz = timezone.get_current_timezone()
                end_to = timezone.make_aware(
                    datetime.combine(parsed_to + timedelta(days=1), time.min), tz
                )
                queryset = queryset.filter(scheduled_at__lt=end_to)

        if period:
            base_date = parse_date(base_date_raw) if base_date_raw else timezone.localdate()
            if base_date is None:
                queryset = queryset.none()
            elif period == "day":
                start_date = base_date
                end_date = base_date + timedelta(days=1)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)
            elif period == "week":
                start_date = base_date - timedelta(days=base_date.weekday())
                end_date = start_date + timedelta(days=7)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)
            elif period == "month":
                start_date = base_date.replace(day=1)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
                end_dt = timezone.make_aware(datetime.combine(end_date, time.min), tz)
                queryset = queryset.filter(scheduled_at__gte=start_dt, scheduled_at__lt=end_dt)

        return queryset


class AppointmentChangeRequestViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = AppointmentChangeRequest.objects.select_related(
        "appointment", "appointment__client", "appointment__tattooer", "requested_by"
    )
    serializer_class = AppointmentChangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "accept": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "reject": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
    }

    def get_queryset(self):
        scope = user_appointment_scope_queryset(self.request.user)
        qs = self.queryset.filter(appointment__in=scope)
        aid = self.request.query_params.get("appointment")
        if aid and aid.isdigit():
            qs = qs.filter(appointment_id=int(aid))
        return qs

    def perform_create(self, serializer):
        cr = serializer.save(requested_by=self.request.user)
        notify_change_request_created(cr)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        cr = self.get_object()
        if not can_respond_to_change_request(request.user, cr):
            return Response(
                {"detail": "Sem permissao para aceitar esta solicitacao."},
                status=status.HTTP_403_FORBIDDEN,
            )
        appt_id = cr.appointment_id
        with transaction.atomic():
            try:
                apply_accepted_change_request(cr, request)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except serializers.ValidationError as exc:
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
            cr.status = AppointmentChangeRequest.STATUS_ACCEPTED
            cr.save(update_fields=["status", "updated_at"])
            AppointmentChangeRequest.objects.filter(
                appointment_id=appt_id, status=AppointmentChangeRequest.STATUS_PENDING
            ).exclude(pk=cr.pk).update(status=AppointmentChangeRequest.STATUS_REJECTED)
        appt = Appointment.objects.select_related(
            "client", "tattooer", "client__health_form", "source_consultation"
        ).get(pk=appt_id)
        notify_change_request_accepted(appt, actor=request.user)
        out = AppointmentReadSerializer(appt, context={"request": request})
        return Response({"appointment": out.data, "change_request": {"id": cr.id, "status": cr.status}})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        cr = self.get_object()
        if not can_respond_to_change_request(request.user, cr):
            return Response(
                {"detail": "Sem permissao para recusar esta solicitacao."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cr.status = AppointmentChangeRequest.STATUS_REJECTED
        cr.save(update_fields=["status", "updated_at"])
        appt = cr.appointment
        notify_change_request_rejected(appt, actor=request.user)
        return Response(
            AppointmentChangeRequestSerializer(cr, context={"request": request}).data
        )


__all__ = ["AppointmentViewSet", "AppointmentChangeRequestViewSet"]
