"""RNF05: token com expiracao por inatividade."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from studio.models import TokenActivity


def inactivity_timeout() -> timedelta:
    minutes = int(getattr(settings, "TOKEN_INACTIVITY_MINUTES", 30))
    return timedelta(minutes=max(1, minutes))


def touch_token_activity(token: Token) -> None:
    now = timezone.now()
    TokenActivity.objects.update_or_create(
        token=token,
        defaults={"last_activity": now},
    )


def assert_token_not_expired(token: Token) -> None:
    try:
        activity = token.activity
    except TokenActivity.DoesNotExist:
        touch_token_activity(token)
        return
    if timezone.now() - activity.last_activity > inactivity_timeout():
        token.delete()
        raise exceptions.AuthenticationFailed(
            "Sessao encerrada por inatividade. Faca login novamente.",
            code="session_inactive",
        )


class InactivityTokenAuthentication(TokenAuthentication):
    keyword = "Token"

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        assert_token_not_expired(token)
        touch_token_activity(token)
        return user, token


def issue_token_for_user(user):
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    touch_token_activity(token)
    return token
