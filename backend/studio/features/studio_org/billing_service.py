from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from studio.features.studio_org.billing_repository import get_billing
from studio.models import StudioBilling


def extend_paid_period(days: int | None = None) -> StudioBilling:
    days = days or int(getattr(settings, "SUBSCRIPTION_BILLING_PERIOD_DAYS", 30))
    b = get_billing()
    # Renova a partir do fim do periodo ja pago, nao do dia do pagamento (nao perde dias).
    base = max(timezone.now(), b.paid_until)
    b.paid_until = base + timedelta(days=days)
    b.payment_cancelled_at = None
    b.save(update_fields=["paid_until", "payment_cancelled_at", "updated_at"])
    return b


def mark_subscription_cancelled() -> StudioBilling:
    b = get_billing()
    b.payment_cancelled_at = timezone.now()
    b.save(update_fields=["payment_cancelled_at", "updated_at"])
    return b


def record_payment_attempt(ok: bool, note: str) -> None:
    b = get_billing()
    b.last_payment_attempt_at = timezone.now()
    b.last_payment_attempt_ok = ok
    b.last_payment_attempt_note = (note or "")[:500]
    b.save(
        update_fields=[
            "last_payment_attempt_at",
            "last_payment_attempt_ok",
            "last_payment_attempt_note",
            "updated_at",
        ]
    )
