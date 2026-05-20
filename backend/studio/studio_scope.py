"""
Regras de escopo por estudio (multi-tenant + HU06 / LGPD).

- Cada usuario de painel pertence a um Studio (UserProfile.studio).
- Clientes, tatuadores e agendamentos ficam vinculados ao tenant.
- Ficha de saude: visivel apenas apos atendimento no estudio (exceto o proprio cliente).
"""

from django.contrib.auth.models import User
from django.db.models import QuerySet

from studio.models import Appointment, Client, Studio, Tattooer, UserProfile


def default_studio() -> Studio:
    """
    Estudio padrao (pk=1) para dev e legado.

    Em producao, todo UserProfile de painel deve ter studio_id apos registro/login.
    """
    return Studio.objects.get_or_create(
        pk=1,
        defaults={"name": "Estudio principal", "is_active": True},
    )[0]


def ensure_profile_studio(profile: UserProfile) -> int:
    if profile.studio_id:
        return profile.studio_id
    studio = default_studio()
    profile.studio_id = studio.pk
    profile.save(update_fields=["studio_id"])
    return studio.pk


def get_user_studio_id(user: User) -> int:
    profile, _ = UserProfile.objects.select_related("studio").get_or_create(user=user)
    return ensure_profile_studio(profile)


def client_ids_served_by_studio(studio_id: int):
    """Clientes com sessao nao cancelada neste estudio (criterio HU06)."""
    return (
        Appointment.objects.filter(studio_id=studio_id)
        .exclude(status=Appointment.STATUS_CANCELLED)
        .values_list("client_id", flat=True)
        .distinct()
    )


def client_ids_served_by_tattooer_at_studio(studio_id: int, tattooer_id: int):
    return (
        Appointment.objects.filter(studio_id=studio_id, tattooer_id=tattooer_id)
        .exclude(status=Appointment.STATUS_CANCELLED)
        .values_list("client_id", flat=True)
        .distinct()
    )


def filter_clients_for_user(queryset: QuerySet, user: User) -> QuerySet:
    """Lista de clientes conforme papel e tenant."""
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    if profile.role == UserProfile.ROLE_STUDIO:
        return queryset.filter(studio_id=get_user_studio_id(user))
    if profile.role == UserProfile.ROLE_TATTOOER:
        if not profile.tattooer_id:
            return queryset.none()
        studio_id = ensure_profile_studio(profile)
        ids = client_ids_served_by_tattooer_at_studio(studio_id, profile.tattooer_id)
        return queryset.filter(id__in=ids)
    return queryset


def filter_tattooers_for_user(queryset: QuerySet, user: User, studio_param: str | None) -> QuerySet:
    """Tatuadores do tenant; clientes podem filtrar ?studio= ao agendar."""
    if studio_param and str(studio_param).isdigit():
        return queryset.filter(studio_id=int(studio_param))
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.role == UserProfile.ROLE_STUDIO:
        return queryset.filter(studio_id=get_user_studio_id(user))
    return queryset


def filter_health_forms_by_studio_access(queryset, user: User):
    """Ficha de saude (HU06): apenas clientes ja atendidos no estudio."""
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    role = profile.role
    if role == UserProfile.ROLE_STUDIO:
        studio_id = ensure_profile_studio(profile)
        return queryset.filter(client_id__in=client_ids_served_by_studio(studio_id))
    if role == UserProfile.ROLE_TATTOOER:
        if not profile.tattooer_id:
            return queryset.none()
        studio_id = ensure_profile_studio(profile)
        ids = client_ids_served_by_tattooer_at_studio(studio_id, profile.tattooer_id)
        return queryset.filter(client_id__in=ids)
    return queryset


def filter_client_queryset_by_studio_access(queryset, user: User):
    """Alias legado: mesmo criterio de filter_clients_for_user para tatuador."""
    return filter_clients_for_user(queryset, user)


def tattooer_has_blocking_appointments(tattooer: Tattooer) -> bool:
    return tattooer.appointments.exclude(status=Appointment.STATUS_CANCELLED).exists()


def client_has_blocking_appointments(client: Client) -> bool:
    return client.appointments.exclude(status=Appointment.STATUS_CANCELLED).exists()


def cleanup_linked_records_for_account(user: User) -> None:
    """Ao excluir conta: remove Client vinculado; tatuador so desvincula cadastro."""
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    if profile.role == UserProfile.ROLE_CLIENT:
        email = (user.email or "").strip()
        if email:
            Client.objects.filter(email__iexact=email).delete()
    elif profile.role == UserProfile.ROLE_TATTOOER:
        profile.tattooer = None
        profile.save(update_fields=["tattooer"])


def account_user_has_blocking_appointments(user: User) -> bool:
    profile, _ = UserProfile.objects.select_related("tattooer").get_or_create(user=user)
    if profile.role == UserProfile.ROLE_CLIENT:
        email = (user.email or "").strip()
        if not email:
            return False
        return (
            Appointment.objects.filter(client__email__iexact=email)
            .exclude(status=Appointment.STATUS_CANCELLED)
            .exists()
        )
    if profile.role == UserProfile.ROLE_TATTOOER and profile.tattooer_id:
        return tattooer_has_blocking_appointments(profile.tattooer)
    return False
