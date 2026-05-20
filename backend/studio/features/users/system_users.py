"""HU05: listagem unificada de usuarios do sistema."""

from django.contrib.auth.models import User
from django.db.models import Q

from studio.models import Client, Tattooer, UserProfile


def build_system_users_queryset(
    q: str | None,
    role: str | None,
    is_active: str | None,
    studio_id: int | None = None,
):
    entries = []
    seen_emails: set[str] = set()

    users = User.objects.select_related("profile").all()
    if studio_id:
        users = users.filter(profile__studio_id=studio_id)
    valid_roles = {r[0] for r in UserProfile.ROLE_CHOICES}
    if role in valid_roles:
        users = users.filter(profile__role=role)
    if is_active in {"true", "false"}:
        users = users.filter(is_active=(is_active == "true"))
    if q:
        users = users.filter(
            Q(first_name__icontains=q)
            | Q(email__icontains=q)
            | Q(username__icontains=q)
        )

    for user in users:
        profile = getattr(user, "profile", None)
        if profile is None:
            profile, _ = UserProfile.objects.get_or_create(user=user)
        email = (user.email or "").strip().lower()
        if email:
            seen_emails.add(email)
        contact = ""
        client_id = None
        tattooer_id = None
        if profile.role == UserProfile.ROLE_CLIENT and email:
            client = Client.objects.filter(email__iexact=email).first()
            if client:
                client_id = client.id
                contact = client.phone
        elif profile.role == UserProfile.ROLE_TATTOOER and profile.tattooer_id:
            tattooer_id = profile.tattooer_id
            t = profile.tattooer
            if t:
                contact = t.contact
        entries.append(
            {
                "id": f"account:{user.pk}",
                "source": "account",
                "source_id": user.pk,
                "role": profile.role,
                "name": user.first_name or user.username,
                "email": user.email or "",
                "contact": contact,
                "is_active": user.is_active,
                "account_user_id": user.pk,
                "client_id": client_id,
                "tattooer_id": tattooer_id,
                "studio_id": profile.studio_id,
            }
        )

    clients = Client.objects.all()
    if studio_id:
        from studio.models import Appointment

        client_ids = (
            Appointment.objects.filter(studio_id=studio_id)
            .exclude(status="cancelled")
            .values_list("client_id", flat=True)
            .distinct()
        )
        clients = clients.filter(id__in=client_ids)
    if role == UserProfile.ROLE_CLIENT:
        pass
    elif role in (UserProfile.ROLE_TATTOOER, UserProfile.ROLE_STUDIO):
        clients = Client.objects.none()
    if is_active in {"true", "false"}:
        clients = clients.filter(is_active=(is_active == "true"))
    if q:
        clients = clients.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    for client in clients:
        email = (client.email or "").strip().lower()
        if email and email in seen_emails:
            continue
        entries.append(
            {
                "id": f"client:{client.pk}",
                "source": "client",
                "source_id": client.pk,
                "role": UserProfile.ROLE_CLIENT,
                "name": client.name,
                "email": client.email,
                "contact": client.phone,
                "is_active": client.is_active,
                "account_user_id": None,
                "client_id": client.pk,
                "tattooer_id": None,
                "studio_id": None,
            }
        )

    tattooers = Tattooer.objects.select_related("studio").all()
    if studio_id:
        tattooers = tattooers.filter(studio_id=studio_id)
    if role == UserProfile.ROLE_TATTOOER:
        pass
    elif role in (UserProfile.ROLE_CLIENT, UserProfile.ROLE_STUDIO):
        tattooers = Tattooer.objects.none()
    if is_active in {"true", "false"}:
        tattooers = tattooers.filter(is_active=(is_active == "true"))
    if q:
        tattooers = tattooers.filter(
            Q(name__icontains=q)
            | Q(artistic_style__icontains=q)
            | Q(contact__icontains=q)
        )

    linked_tattooer_ids = set(
        UserProfile.objects.filter(
            role=UserProfile.ROLE_TATTOOER,
            tattooer_id__isnull=False,
        ).values_list("tattooer_id", flat=True)
    )

    for tattooer in tattooers:
        if tattooer.pk in linked_tattooer_ids:
            continue
        entries.append(
            {
                "id": f"tattooer:{tattooer.pk}",
                "source": "tattooer",
                "source_id": tattooer.pk,
                "role": UserProfile.ROLE_TATTOOER,
                "name": tattooer.name,
                "email": "",
                "contact": tattooer.contact,
                "is_active": tattooer.is_active,
                "account_user_id": None,
                "client_id": None,
                "tattooer_id": tattooer.pk,
                "studio_id": tattooer.studio_id,
            }
        )

    entries.sort(key=lambda e: (e["role"], e["name"].lower()))
    return entries
