"""Acesso a StudioBilling do tenant (get_or_create via org_services)."""

from studio.features.studio_org.org_services import get_billing_for_studio
from studio.models import StudioBilling
from studio.studio_scope import default_studio


def get_billing(studio_id: int | None = None) -> StudioBilling:
    sid = studio_id or default_studio().pk
    billing = get_billing_for_studio(sid)
    return StudioBilling.objects.select_related("studio").get(pk=billing.pk)
