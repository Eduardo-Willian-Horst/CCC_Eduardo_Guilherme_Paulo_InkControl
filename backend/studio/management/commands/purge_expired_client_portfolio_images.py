from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.models import Appointment, ClientPortfolioImage


class Command(BaseCommand):
    help = (
        "Remove imagens de portfolio de clientes cuja ultima sessao concluida "
        "foi ha mais de 7 dias e nao ha sessoes ativas (HU10)."
    )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=7)
        active_statuses = {
            Appointment.STATUS_REQUESTED,
            Appointment.STATUS_WAITING_BUDGET,
            Appointment.STATUS_CONFIRMED,
            Appointment.STATUS_IN_PROGRESS,
        }
        active_client_ids = set(
            Appointment.objects.filter(status__in=active_statuses).values_list(
                "client_id", flat=True
            )
        )
        done_old_client_ids = set(
            Appointment.objects.filter(
                status=Appointment.STATUS_DONE,
                updated_at__lt=cutoff,
            ).values_list("client_id", flat=True)
        )
        eligible = done_old_client_ids - active_client_ids
        removed = 0
        for img in ClientPortfolioImage.objects.filter(client_id__in=eligible).iterator():
            img.image.delete(save=False)
            img.delete()
            removed += 1
        self.stdout.write(self.style.SUCCESS(f"Imagens de portfolio removidas: {removed}"))
