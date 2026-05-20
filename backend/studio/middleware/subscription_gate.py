from django.http import JsonResponse

from studio.models import StudioBilling


def _path_allowed(path: str) -> bool:
    if path.startswith("/api/studio/subscription"):
        return True
    allowed = {
        "/api/health/",
        "/api/auth/register/",
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
            billing = StudioBilling.get_solo()
        except Exception:
            return self.get_response(request)
        if billing.is_access_allowed():
            return self.get_response(request)
        payload = {
            "detail": "Assinatura inativa ou periodo pago expirado. Renove em /api/studio/subscription/pay/.",
            "code": "subscription_required",
        }
        return JsonResponse(payload, status=402)
