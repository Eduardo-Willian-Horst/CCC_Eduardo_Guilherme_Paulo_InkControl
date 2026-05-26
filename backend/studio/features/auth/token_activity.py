"""RNF05: token com expiracao por inatividade."""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, OperationalError
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from studio.models import TokenActivity


def inactivity_timeout() -> timedelta:
    minutes = int(getattr(settings, "TOKEN_INACTIVITY_MINUTES", 30))
    return timedelta(minutes=max(1, minutes))


def activity_touch_interval() -> timedelta:
    seconds = int(getattr(settings, "TOKEN_ACTIVITY_TOUCH_INTERVAL_SECONDS", 60))
    return timedelta(seconds=max(0, seconds))


def is_sqlite_locked(exc: OperationalError) -> bool:
    return "database is locked" in str(exc).lower()


def touch_token_activity(token: Token, *, force: bool = False) -> None:
    now = timezone.now()
    try:
        activity = token.activity
        if not force and now - activity.last_activity < activity_touch_interval():
            return
        TokenActivity.objects.filter(pk=activity.pk).update(last_activity=now)
        activity.last_activity = now
    except TokenActivity.DoesNotExist:
        try:
            TokenActivity.objects.create(token=token, last_activity=now)
        except IntegrityError:
            TokenActivity.objects.filter(token=token).update(last_activity=now)
    except OperationalError as exc:
        if is_sqlite_locked(exc):
            return
        raise


def assert_token_not_expired(token: Token) -> None:
    try:
        activity = token.activity
    except TokenActivity.DoesNotExist:
        touch_token_activity(token, force=True)
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
