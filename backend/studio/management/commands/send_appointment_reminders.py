"""HU18: e-mail ~30 min antes do horario agendado (janela configuravel no comando)."""

from datetime import timedelta


from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.features.notifications.appointment_email import recipient_emails_for_appointment
from studio.features.notifications.email_service import send_plain_email
from studio.models import Appointment


class Command(BaseCommand):
    help = "Envia e-mail de lembrete ~30 minutos antes do horario agendado (DVP HU18)."

    def handle(self, *args, **options):
        now = timezone.now()
        window_start = now + timedelta(minutes=25)
        window_end = now + timedelta(minutes=35)
        qs = (
            Appointment.objects.filter(
                scheduled_at__gte=window_start,
                scheduled_at__lte=window_end,
                reminder_email_sent_at__isnull=True,
            )
            .exclude(status=Appointment.STATUS_CANCELLED)
            .exclude(status=Appointment.STATUS_DONE)
            .select_related("client", "tattooer")
        )
        sent = 0
        for appt in qs.iterator():
            recipients = recipient_emails_for_appointment(appt)
            if not recipients:
                continue
            subject = f"[InkControl] Lembrete: sessao em cerca de 30 minutos (#{appt.pk})"
            body = (
                f"Lembrete: voce tem agendamento #{appt.pk}\n"
                f"Cliente: {appt.client.name}\n"
                f"Tatuador: {appt.tattooer.name}\n"
                f"Horario: {appt.scheduled_at.isoformat()}\n"
            )
            send_plain_email(subject, body, recipients)
            Appointment.objects.filter(pk=appt.pk).update(reminder_email_sent_at=now)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Lembretes enviados: {sent}"))
