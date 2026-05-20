"""Gera token de reset e envia link por e-mail (FRONTEND_PASSWORD_RESET_URL)."""

from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from studio.features.notifications.email_service import send_plain_email

_token_generator = PasswordResetTokenGenerator()


def request_password_reset(email: str) -> bool:
    # Sempre retorna True para nao revelar se o e-mail esta cadastrado (enumeracao de contas).
    email_clean = (email or "").strip().lower()
    if not email_clean:
        return True
    user = User.objects.filter(email__iexact=email_clean, is_active=True).first()
    if user is None:
        return True
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = _token_generator.make_token(user)
    base = getattr(
        settings,
        "FRONTEND_PASSWORD_RESET_URL",
        "http://localhost:5173/redefinir-senha",
    ).rstrip("/")
    link = f"{base}?uid={uid}&token={token}"
    subject = "[InkControl] Redefinicao de senha"
    body = (
        "Voce solicitou redefinir sua senha no InkControl.\n\n"
        f"Acesse o link (valido por tempo limitado):\n{link}\n\n"
        "Se nao foi voce, ignore este e-mail."
    )
    send_plain_email(subject, body, [user.email])
    return True


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> tuple[bool, str]:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=int(uid))
    except (ValueError, TypeError, OverflowError, User.DoesNotExist):
        return False, "Link invalido ou expirado."
    if not _token_generator.check_token(user, token):
        return False, "Link invalido ou expirado."
    if len(new_password) < 8:
        return False, "Senha deve ter no minimo 8 caracteres."
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True, ""
