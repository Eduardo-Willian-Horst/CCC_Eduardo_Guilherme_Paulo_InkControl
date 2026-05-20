"""Cadastro de usuario cliente/tatuador (nao cria estudio)."""

from django.contrib.auth.models import User

from studio.features.studio_org.org_services import ensure_studio_org
from studio.models import UserProfile
from studio.services.exceptions import ServiceValidationError
from studio.studio_scope import default_studio


def register_app_user(*, name: str, email: str, password: str, role: str) -> User:
    email = email.lower().strip()
    if role == UserProfile.ROLE_STUDIO:
        raise ServiceValidationError(
            {"role": "Para cadastrar um estudio use POST /api/studios/register/."}
        )
    if User.objects.filter(email__iexact=email).exists():
        raise ServiceValidationError({"email": "Este e-mail ja esta em uso."})
    user = User.objects.create_user(
        username=email,
        first_name=name,
        email=email,
        password=password,
    )
    studio = default_studio()
    ensure_studio_org(studio)
    UserProfile.objects.create(user=user, role=role, studio=studio)
    return user
