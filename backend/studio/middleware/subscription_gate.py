"""
HU16: bloqueia API do tenant se a mensalidade (paid_until) expirou.

Rotas de login, registro de estudio e pagamento permanecem acessiveis.
"""

import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _path_allowed(path: str) -> bool:
    if path.startswith("/api/studio/subscription"):
        return True
    if path.startswith("/api/studios/register"):
        return True
    allowed = {
        "/api/health/",
        "/api/auth/register/",
        "/api/studios/register/",
        "/api/auth/login/",
        "/api/auth/logout/",
        "/api/auth/password-reset/request/",
        "/api/auth/password-reset/confirm/",
    }
    return path in allowed


def _user_from_token(request):
    raw = request.headers.get("Authorization") or ""
    if not raw.startswith("Token "):
        return None
    key = raw[6:].strip()
    if not key:
        return None
    from rest_framework.authtoken.models import Token

    try:
        return Token.objects.select_related("user").get(key=key).user
    except Token.DoesNotExist:
        return None


class SubscriptionGateMiddleware:
    # Token valido + paid_until expirado -> 402; rotas de login/subscription/pay ficam liberadas.

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        if not getattr(settings, "SUBSCRIPTION_GATE_ENABLED", True):
            return self.get_response(request)
        if not request.path.startswith("/api/") or _path_allowed(request.path):
            return self.get_response(request)
        user = _user_from_token(request)
        if user is None or not user.is_authenticated:
            return self.get_response(request)
        try:
            from studio.studio_scope import get_user_studio_id

            studio_id = get_user_studio_id(user)
            from studio.features.studio_org.org_services import get_billing_for_studio

            billing = get_billing_for_studio(studio_id)
        except Exception:
            logger.exception("Falha ao verificar assinatura; requisicao segue sem gate.")
            return self.get_response(request)
        if billing.is_access_allowed():
            return self.get_response(request)
        payload = {
            "detail": "Assinatura inativa ou periodo pago expirado. Renove em /api/studio/subscription/pay/.",
            "code": "subscription_required",
        }
        return JsonResponse(payload, status=402)
