"""RNF06: bloqueio de login apos tentativas invalidas por conta."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from studio.models import UserProfile


def _max_attempts() -> int:
    return int(getattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 5))


def _lockout_duration() -> timedelta:
    minutes = int(getattr(settings, "LOGIN_LOCKOUT_MINUTES", 15))
    return timedelta(minutes=max(1, minutes))


def is_login_locked(user: User) -> tuple[bool, str | None]:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    locked_until = profile.login_locked_until
    if locked_until and locked_until > timezone.now():
        remaining = int((locked_until - timezone.now()).total_seconds() // 60) + 1
        return True, (
            f"Conta temporariamente bloqueada apos varias tentativas invalidas. "
            f"Tente novamente em cerca de {remaining} minuto(s)."
        )
    if locked_until and locked_until <= timezone.now():
        profile.failed_login_count = 0
        profile.login_locked_until = None
        profile.save(update_fields=["failed_login_count", "login_locked_until"])
    return False, None


def record_failed_login(user: User) -> str | None:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.failed_login_count += 1
    if profile.failed_login_count >= _max_attempts():
        profile.login_locked_until = timezone.now() + _lockout_duration()
        profile.save(update_fields=["failed_login_count", "login_locked_until"])
        return (
            f"Conta bloqueada por {_lockout_duration().seconds // 60} minutos "
            f"apos {_max_attempts()} tentativas invalidas."
        )
    profile.save(update_fields=["failed_login_count"])
    return None


def reset_login_attempts(user: User) -> None:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.failed_login_count or profile.login_locked_until:
        profile.failed_login_count = 0
        profile.login_locked_until = None
        profile.save(update_fields=["failed_login_count", "login_locked_until"])
