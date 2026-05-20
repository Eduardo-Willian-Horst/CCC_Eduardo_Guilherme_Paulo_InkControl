"""HU10: remove reference_image de agendamentos done ha mais de 7 dias."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.models import Appointment


class Command(BaseCommand):
    help = (
        "Remove imagens de referencia de agendamentos concluidos ha mais de 7 dias "
        "(HU10 / retencao)."
    )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=7)
        qs = Appointment.objects.filter(
            status=Appointment.STATUS_DONE,
            updated_at__lt=cutoff,
        )
        removed = 0
        for appt in qs.iterator():
            if not appt.reference_image:
                continue
            appt.reference_image.delete(save=False)
            appt.save(update_fields=["reference_image", "updated_at"])
            removed += 1
        self.stdout.write(self.style.SUCCESS(f"Processados {removed} agendamento(s)."))
