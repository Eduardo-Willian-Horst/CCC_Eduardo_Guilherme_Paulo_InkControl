"""
Bootstrap de tenant: cada Studio tem StudioSettings (expediente, HU12) e StudioBilling (HU16).

Usado no registro de estudio, migrate e servicos que precisam de paid_until / horario.
"""

from datetime import time, timedelta

from django.utils import timezone

from studio.models import Studio, StudioBilling, StudioSettings


def get_settings_for_studio(studio_id: int) -> StudioSettings:
    studio = Studio.objects.get(pk=studio_id)
    obj, _ = StudioSettings.objects.get_or_create(
        studio=studio,
        defaults={
            "opens_at": time(9, 0),
            "closes_at": time(18, 0),
            "offers_consultation": True,
        },
    )
    return obj


def get_billing_for_studio(studio_id: int) -> StudioBilling:
    studio = Studio.objects.get(pk=studio_id)
    obj, created = StudioBilling.objects.get_or_create(
        studio=studio,
        defaults={"paid_until": timezone.now() + timedelta(days=3650)},
    )
    return obj


def ensure_studio_org(studio: Studio) -> tuple[StudioSettings, StudioBilling]:
    settings = get_settings_for_studio(studio.pk)
    billing = get_billing_for_studio(studio.pk)
    return settings, billing


def create_studio_with_org(name: str) -> Studio:
    studio = Studio.objects.create(name=name[:120], is_active=True)
    ensure_studio_org(studio)
    return studio
