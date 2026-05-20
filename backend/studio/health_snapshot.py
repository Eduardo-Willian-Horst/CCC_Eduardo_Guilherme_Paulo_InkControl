"""HU06: copia imutavel da ficha de saude no momento do agendamento."""

from django.utils import timezone

from studio.models import Client


def build_health_snapshot(client: Client) -> dict:
    hf = getattr(client, "health_form", None)
    if hf is None:
        return {}
    return {
        "allergies": hf.allergies or "",
        "chronic_diseases": hf.chronic_diseases or "",
        "healing_history": hf.healing_history or "",
        "notes": hf.notes or "",
        "captured_at": timezone.now().isoformat(),
    }
