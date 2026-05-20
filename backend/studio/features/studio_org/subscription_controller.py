from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.features.notifications.email_service import send_plain_email
from studio.features.studio_org.billing_repository import get_billing
from studio.features.studio_org.billing_service import (
    extend_paid_period,
    mark_subscription_cancelled,
    record_payment_attempt,
)
from studio.models import UserProfile
from studio.permissions import get_user_role


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
        b = get_billing()
        now = timezone.now()
        return Response(
            {
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
        days = int(getattr(settings, "SUBSCRIPTION_BILLING_PERIOD_DAYS", 30))
        note = (request.data.get("note") or "Pagamento simulado (sem gateway)").strip()[:500]
        extend_paid_period(days=days)
        record_payment_attempt(True, note)
        b = get_billing()
        recipients = [(request.user.email or "").strip()]
        subject = "[InkControl] Pagamento da mensalidade"
        body = (
            f"Pagamento registrado com sucesso.\n"
            f"Detalhe: {note}\n"
            f"Acesso ate: {b.paid_until.isoformat()}\n"
        )
        send_plain_email(subject, body, [e for e in recipients if e])
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
        mark_subscription_cancelled()
        record_payment_attempt(True, "Cancelamento de renovacao automatica solicitado.")
        b = get_billing()
        recipients = [(request.user.email or "").strip()]
        send_plain_email(
            "[InkControl] Mensalidade cancelada",
            (
                "A renovacao automatica foi cancelada. O acesso permanece ate "
                f"{b.paid_until.isoformat()}.\n"
            ),
            [e for e in recipients if e],
        )
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
