"""
Assinatura do tenant (HU16/HU20): status, pagamento simulado e cancelamento.

O middleware subscription_gate bloqueia a API se paid_until expirou; estas rotas ficam liberadas.
"""

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.features.studio_org.billing_repository import get_billing
from studio.services.billing_notifications import notify_payment_attempt
from studio.features.studio_org.billing_service import (
    extend_paid_period,
    mark_subscription_cancelled,
    record_payment_attempt,
)
from studio.models import UserProfile
from studio.permissions import get_user_role
from studio.studio_scope import get_user_studio_id


def _require_studio(request):
    if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
        return Response(status=status.HTTP_403_FORBIDDEN)
    return None


class StudioSubscriptionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        deny = _require_studio(request)
        if deny:
            return deny
        sid = get_user_studio_id(request.user)
        b = get_billing(sid)
        now = timezone.now()
        return Response(
            {
                "studio_id": sid,
                "paid_until": b.paid_until,
                "is_active": b.is_access_allowed(now),
                "payment_cancelled_at": b.payment_cancelled_at,
                "last_payment_attempt_at": b.last_payment_attempt_at,
                "last_payment_attempt_ok": b.last_payment_attempt_ok,
                "last_payment_attempt_note": b.last_payment_attempt_note,
            }
        )


class StudioSubscriptionPayView(APIView):
    # HU16: estende paid_until sem gateway; em producao trocar por webhook do provedor de pagamento.

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        deny = _require_studio(request)
        if deny:
            return deny
        sid = get_user_studio_id(request.user)
        days = int(getattr(settings, "SUBSCRIPTION_BILLING_PERIOD_DAYS", 30))
        note = (request.data.get("note") or "Pagamento simulado (sem gateway)").strip()[:500]
        recipients = [(request.user.email or "").strip()]
        simulate_fail = str(request.data.get("simulate_failure", "")).lower() in (
            "1",
            "true",
            "yes",
        )
        if simulate_fail:
            record_payment_attempt(False, note or "Pagamento recusado (simulado).", studio_id=sid)
            b = get_billing(sid)
            notify_payment_attempt(b, ok=False, note=note, recipient_emails=recipients)
            return Response(
                {
                    "detail": "Pagamento nao concluido.",
                    "code": "payment_failed",
                    "paid_until": b.paid_until,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        extend_paid_period(days=days, studio_id=sid)
        record_payment_attempt(True, note, studio_id=sid)
        b = get_billing(sid)
        notify_payment_attempt(b, ok=True, note=note, recipient_emails=recipients)
        return Response(
            {
                "detail": "Mensalidade atualizada.",
                "paid_until": b.paid_until,
            }
        )


class StudioSubscriptionCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        deny = _require_studio(request)
        if deny:
            return deny
        sid = get_user_studio_id(request.user)
        mark_subscription_cancelled(studio_id=sid)
        cancel_note = "Cancelamento de renovacao automatica solicitado."
        record_payment_attempt(True, cancel_note, studio_id=sid)
        b = get_billing(sid)
        recipients = [(request.user.email or "").strip()]
        notify_payment_attempt(b, ok=True, note=cancel_note, recipient_emails=recipients)
        return Response(
            {
                "detail": "Renovacao cancelada; acesso ate o fim do periodo ja pago.",
                "paid_until": b.paid_until,
                "payment_cancelled_at": b.payment_cancelled_at,
            }
        )


__all__ = [
    "StudioSubscriptionStatusView",
    "StudioSubscriptionPayView",
    "StudioSubscriptionCancelView",
]
